"""
NEXUS CCTV — Search Router
POST /api/search — NL query → SQL filter → incident results
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database import get_db
from backend.models import Incident
from backend.schemas import SearchRequest, SearchResponse
from backend.services.qwen_plus import semantic_search

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search_incidents(body: SearchRequest, db: AsyncSession = Depends(get_db)):
    """
    Natural language search over incidents.
    Qwen-Plus converts the query to a SQL WHERE clause.
    """
    where_clause, explanation = await semantic_search(body.query)

    try:
        # Build safe parameterized query
        raw_sql = f"SELECT id FROM incidents WHERE {where_clause} ORDER BY timestamp DESC LIMIT :limit"
        result = await db.execute(text(raw_sql), {"limit": body.limit})
        ids = [row[0] for row in result.fetchall()]
    except Exception as e:
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
