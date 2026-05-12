from uuid import UUID
from uuid import uuid4

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import SupabaseClaims, get_token_claims
from app.models.user import User


async def get_current_user(
    claims: SupabaseClaims = Depends(get_token_claims),
    db: AsyncSession = Depends(get_db),
) -> User:
    result = await db.execute(select(User).where(User.id == UUID(claims.user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is authenticated but not registered in this API",
        )
    return user


async def get_request_id(request: Request, x_request_id: str | None = Header(default=None)) -> str:
    state_request_id = getattr(request.state, "request_id", None)
    if state_request_id:
        return state_request_id
    if x_request_id and x_request_id.strip():
        return x_request_id.strip()[:120]
    return str(uuid4())
