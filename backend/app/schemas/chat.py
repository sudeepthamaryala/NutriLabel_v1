from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ChatRole, ChatSessionType


class ChatSessionCreate(BaseModel):
    type: ChatSessionType
    title: str = Field(min_length=1, max_length=255)


class ChatSessionRead(BaseModel):
    id: UUID
    user_id: UUID
    type: ChatSessionType
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatMessageCreate(BaseModel):
    role: ChatRole
    content: str = Field(min_length=1)
    image_url: str | None = None
    metadata: dict = Field(default_factory=dict)


class ChatMessageRead(BaseModel):
    id: UUID
    session_id: UUID
    role: ChatRole
    content: str
    image_url: str | None = None
    metadata: dict = Field(default_factory=dict, validation_alias="metadata_")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
