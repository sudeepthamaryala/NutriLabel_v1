from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ActivityLevel, HealthGoal, Sex


class HealthProfileBase(BaseModel):
    age: int = Field(ge=1, le=120)
    weight_kg: Decimal = Field(gt=0, le=500, decimal_places=2)
    height_cm: Decimal = Field(gt=0, le=300, decimal_places=2)
    sex: Sex
    activity_level: ActivityLevel
    goal: HealthGoal
    allergies: list[str] = Field(default_factory=list)
    diseases: list[str] = Field(default_factory=list)
    dietary_preferences: list[str] = Field(default_factory=list)


class HealthProfileUpsert(HealthProfileBase):
    pass


class HealthProfileRead(HealthProfileBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

