from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import logging
import re

from backend.database import get_db
from backend.models import Incident
from backend.schemas import SearchRequest, SearchResponse
from backend.services.qwen_plus import semantic_search

router = APIRouter(prefix="/api/search", tags=["search"])
logger = logging.getLogger(__name__)


def is_safe_where_clause(clause: str) -> bool:
    """
    Validates the generated SQL WHERE clause against a strict whitelist.
    Only allows permitted columns, safe operators, functions, and string/integer literals.
    """
    clause = clause.strip()
    if not clause:
        return True

    # 1. Reject semicolons and comment markers to prevent query stacking and comment injection
    if ";" in clause or "--" in clause or "/*" in clause:
        logger.warning(f"SQL Injection Check: Rejected due to dangerous characters in: {clause}")
        return False

    # 2. Extract single-quoted string literals and validate their content
    string_literals = re.findall(r"'[^']*'", clause)
    for lit in string_literals:
        # String literals can only contain letters, numbers, spaces, %, -, _, :, /, and commas
        if not re.match(r"^'[a-zA-Z0-9\s%_\-:,]*'$", lit):
            logger.warning(f"SQL Injection Check: Rejected due to unsafe string literal {lit} in: {clause}")
            return False

    # 3. Replace string literals with placeholder token to simplify parsing
    temp_clause = re.sub(r"'[^']*'", "'STRING_LITERAL'", clause)

    # 4. Tokenize the remaining clause (words, numbers, operators, and punctuation)
    tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*|[0-9]+|!=|<=|>=|[=()<>,\-+*/]", temp_clause)

    allowed_columns = {"threat_type", "severity", "timestamp", "scene_description", "camera_id", "status"}
    dangerous_keywords = {"select", "union", "insert", "update", "delete", "drop", "alter", "exec", "execute", "create", "table"}

    for token in tokens:
        token_lower = token.lower()
        if token_lower in dangerous_keywords:
            logger.warning(f"SQL Injection Check: Rejected due to dangerous keyword '{token}' in: {clause}")
            return False

        if token.isdigit():
            continue

        if token in {"=", "!=", "<", ">", "<=", ">=", "(", ")", ",", "+", "-", "*", "/"}:
            continue

        if token_lower in allowed_columns:
            continue

        if token_lower in {"and", "or", "not", "like", "is", "null", "date", "datetime", "string_literal"}:
            continue

        # If token is not allowed
        logger.warning(f"SQL Injection Check: Rejected due to disallowed token '{token}' in: {clause}")
        return False

    return True


@router.post("", response_model=SearchResponse)
async def search_incidents(body: SearchRequest, db: AsyncSession = Depends(get_db)):
    """
    Natural language search over incidents.
    Qwen-Plus converts the query to a SQL WHERE clause.
    """
    where_clause, explanation = await semantic_search(body.query)

    # Hardening: Validate and sanitize where_clause
    if not is_safe_where_clause(where_clause):
        logger.warning(f"SQL Injection Check: Rejected search filter '{where_clause}' for query '{body.query}'")
        where_clause = "1=1"

    try:
        # Build safe parameterized query
        raw_sql = f"SELECT id FROM incidents WHERE {where_clause} ORDER BY timestamp DESC LIMIT :limit"
        result = await db.execute(text(raw_sql), {"limit": body.limit})
        ids = [row[0] for row in result.fetchall()]
    except Exception as e:
        logger.error(f"Search query error for clause '{where_clause}': {e}")
        # Fallback to full list on bad SQL
        result = await db.execute(
            select(Incident.id).order_by(Incident.timestamp.desc()).limit(body.limit)
        )
        ids = [row[0] for row in result.fetchall()]

    # Fetch full incident objects
    incidents = []
    for iid in ids:
        r = await db.execute(
            select(Incident).options(selectinload(Incident.camera)).where(Incident.id == iid)
        )
        inc = r.scalar_one_or_none()
        if inc:
            incidents.append(inc)

    return SearchResponse(
        query=body.query,
        sql_filter=where_clause,
        results=incidents,
        total=len(incidents),
    )

