from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import SupabaseClaims
from app.models.user import User
from app.schemas.auth import RegisterRequest


async def register_user(
    *,
    db: AsyncSession,
    claims: SupabaseClaims,
    data: RegisterRequest,
) -> User:
    token_email = claims.email.lower()
    if data.email and data.email.lower() != token_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request email must match authenticated token email",
        )

    user_id = UUID(claims.user_id)
    existing = await db.get(User, user_id)
    if existing is not None:
        return existing

    email_owner = await db.execute(select(User).where(User.email == token_email))
    if email_owner.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered to another user",
        )

    user = User(id=user_id, email=token_email, full_name=data.full_name.strip())
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User could not be registered because of a data conflict",
        )

    await db.refresh(user)
    return user

