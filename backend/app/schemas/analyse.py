from uuid import UUID

from pydantic import BaseModel, Field


class NutritionData(BaseModel):
    calories: float | None = None
    total_fat_g: float | None = None
    protein_g: float | None = None
    sugar_g: float | None = None
    sodium_mg: float | None = None
    serving_size: str | None = None
    ingredients: list[str] = Field(default_factory=list)


class AnalyseAnswer(BaseModel):
    summary: str
    recommendations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AnalyseResponse(BaseModel):
    session_id: UUID
    nutrition: NutritionData
    answer: AnalyseAnswer
    confidence: float = Field(ge=0, le=1)
