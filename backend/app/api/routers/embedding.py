import asyncio

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.core.embeddings import EMBEDDING_DIMENSIONS, embed_text

router = APIRouter(tags=["embedding"])


class EmbedRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class EmbedResponse(BaseModel):
    embedding: list[float]


@router.post("/embed", response_model=EmbedResponse)
async def embed(data: EmbedRequest) -> EmbedResponse:
    text = data.text.strip()
    if not text:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="text must not be empty")

    try:
        embedding = await asyncio.to_thread(embed_text, text)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    if len(embedding) != EMBEDDING_DIMENSIONS:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="embedding dimension mismatch")
    return EmbedResponse(embedding=embedding)
