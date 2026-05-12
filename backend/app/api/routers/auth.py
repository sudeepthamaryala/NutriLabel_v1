from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import SupabaseClaims, get_token_claims
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.auth import RegisterRequest, UserRead
from app.services.auth_service import register_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    claims: SupabaseClaims = Depends(get_token_claims),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await register_user(db=db, claims=claims, data=data)


@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user

