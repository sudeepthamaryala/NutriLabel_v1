from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.health_profile import HealthProfile
from app.models.user import User
from app.schemas.profile import HealthProfileRead, HealthProfileUpsert
from app.services.profile_service import get_profile_for_user, upsert_profile_for_user

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=HealthProfileRead)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HealthProfile:
    return await get_profile_for_user(db=db, user_id=current_user.id)


@router.put("", response_model=HealthProfileRead)
async def put_profile(
    data: HealthProfileUpsert,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HealthProfile:
    return await upsert_profile_for_user(db=db, user_id=current_user.id, data=data)

