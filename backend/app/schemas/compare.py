from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.analyse import NutritionData


class ComparedProduct(BaseModel):
    index: int = Field(ge=0)
    nutrition: NutritionData


class CompareVerdict(BaseModel):
    best_product: str
    reasons: list[str] = Field(default_factory=list)
    tradeoffs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CompareResponse(BaseModel):
    session_id: UUID
    products: list[ComparedProduct]
    best_product_index: int = Field(ge=0)
    verdict: CompareVerdict

