"""
Raven AI CCTV — Auth Router
POST /api/auth/login, GET /api/auth/me
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import (
    create_access_token, get_current_operator, hash_password,
    require_operator, verify_password, create_refresh_token
)
from backend.database import get_db
from backend.models import Operator, RefreshToken
from backend.schemas import LoginRequest, OperatorCreate, OperatorOut, Token, TokenRefreshRequest
import hashlib
import uuid
from datetime import timedelta

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=Token)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Operator).where(Operator.username == body.username))
    operator = result.scalar_one_or_none()

    if not operator or not verify_password(body.password, operator.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    if not operator.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    operator.last_login = datetime.now(timezone.utc)
    
    # Generate tokens
    access_token = create_access_token({"sub": operator.username, "role": operator.role.value})
    raw_refresh, hashed_refresh = create_refresh_token()
    family_id = uuid.uuid4().hex
    
    # Store refresh token (expires in 7 days)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    db_refresh = RefreshToken(
        operator_id=operator.id,
        token_hash=hashed_refresh,
        family_id=family_id,
        expires_at=expires_at
    )
    db.add(db_refresh)
    
    await db.commit()
    await db.refresh(operator)

    return Token(
        access_token=access_token,
        refresh_token=raw_refresh,
        operator=OperatorOut.model_validate(operator)
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(body: TokenRefreshRequest, db: AsyncSession = Depends(get_db)):
    token_hash = hashlib.sha256(body.refresh_token.encode()).hexdigest()
    
    # Find token
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    stored_token = result.scalar_one_or_none()
    
    if not stored_token:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
        
    # Check expiry
    if stored_token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired")
        
    # Check reuse / revocation
    if stored_token.revoked:
        # Replay attack detection: revoke all tokens in the same family!
        from sqlalchemy import update
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == stored_token.family_id)
            .values(revoked=True)
        )
        await db.commit()
        raise HTTPException(status_code=401, detail="Token reuse detected. Session revoked.")
        
    # Revoke current token
    stored_token.revoked = True
    
    # Get operator
    result = await db.execute(select(Operator).where(Operator.id == stored_token.operator_id))
    operator = result.scalar_one()
    
    if not operator.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
        
    # Generate new pair
    access_token = create_access_token({"sub": operator.username, "role": operator.role.value})
    raw_refresh, hashed_refresh = create_refresh_token()
    
    new_expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    new_db_token = RefreshToken(
        operator_id=operator.id,
        token_hash=hashed_refresh,
        family_id=stored_token.family_id,
        expires_at=new_expires_at
    )
    db.add(new_db_token)
    await db.commit()
    
    return Token(
        access_token=access_token,
        refresh_token=raw_refresh,
        operator=OperatorOut.model_validate(operator)
    )



@router.get("/me", response_model=OperatorOut)
async def get_me(operator: Operator = Depends(require_operator)):
    return operator


@router.post("/register", response_model=OperatorOut, status_code=201)
async def register(body: OperatorCreate, db: AsyncSession = Depends(get_db)):
    """Create a new operator account (admin only in prod — open for demo)."""
    existing = await db.execute(select(Operator).where(Operator.username == body.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already exists")

    operator = Operator(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
        role=body.role,
    )
    db.add(operator)
    await db.commit()
    await db.refresh(operator)
    return operator
