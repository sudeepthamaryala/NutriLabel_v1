from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RagChunkCreate(BaseModel):
    source: str = Field(min_length=1)
    source_url: str | None = None
    chunk_text: str = Field(min_length=1)
    embedding: list[float] = Field(min_length=384, max_length=384)
    metadata: dict = Field(default_factory=dict)


class RagChunkRead(BaseModel):
    id: UUID
    source: str
    source_url: str | None = None
    chunk_text: str
    metadata: dict = Field(default_factory=dict, validation_alias="metadata_")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
