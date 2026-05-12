from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.health_profile import HealthProfile
from app.schemas.profile import HealthProfileUpsert


async def get_profile_for_user(*, db: AsyncSession, user_id: UUID) -> HealthProfile:
    result = await db.execute(select(HealthProfile).where(HealthProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Health profile not found",
        )
    return profile


async def upsert_profile_for_user(
    *,
    db: AsyncSession,
    user_id: UUID,
    data: HealthProfileUpsert,
) -> HealthProfile:
    result = await db.execute(select(HealthProfile).where(HealthProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    values = data.model_dump()

    if profile is None:
        profile = HealthProfile(user_id=user_id, **values)
        db.add(profile)
    else:
        for field, value in values.items():
            setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)
    return profile

