import asyncio
import re

import httpx
from sqlalchemy import or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.embeddings import EMBEDDING_DIMENSIONS, embed_text
from app.core.retry import retry_async
from app.core.settings import get_settings
from app.models.enums import RagSourceType
from app.models.rag import RagChunk
from app.schemas.analyse import NutritionData


async def retrieve_relevant_chunks(
    *,
    db: AsyncSession,
    question: str | None,
    nutrition: NutritionData,
    limit: int = 3,
) -> list[str]:
    terms = _build_terms(question=question, nutrition=nutrition)
    query_text = _query_text(question=question, nutrition=nutrition)
    embedding = await _embed_query(query_text)
    if embedding:
        vector_chunks = await _retrieve_by_vector(db=db, embedding=embedding, limit=limit)
        if vector_chunks:
            return vector_chunks

    if not terms:
        return []

    try:
        conditions = [RagChunk.chunk_text.ilike(f"%{term}%") for term in terms]
        result = await db.execute(
            select(RagChunk)
            .where(or_(*conditions))
            .order_by(RagChunk.created_at.desc())
            .limit(limit)
        )
    except Exception:
        return []

    return [chunk.chunk_text for chunk in result.scalars().all()]


async def _retrieve_by_vector(*, db: AsyncSession, embedding: list[float], limit: int) -> list[str]:
    vector_literal = "[" + ",".join(str(float(value)) for value in embedding) + "]"
    try:
        result = await db.execute(
            select(RagChunk)
            .order_by(RagChunk.embedding.op("<=>")(vector_literal))
            .limit(limit)
        )
    except Exception:
        return []
    return [chunk.chunk_text for chunk in result.scalars().all()]


async def _embed_query(query_text: str) -> list[float] | None:
    settings = get_settings()
    if not query_text:
        return None

    async def request_embedding() -> httpx.Response:
        async with httpx.AsyncClient(timeout=settings.external_service_timeout_seconds) as client:
            response = await client.post(settings.embedding_service_url, json={"text": query_text})
            response.raise_for_status()
            return response

    if settings.embedding_service_url:
        try:
            response = await retry_async(request_embedding, retries=settings.external_retry_attempts)
            payload = response.json()
        except (httpx.HTTPError, ValueError):
            return None

        embedding = payload.get("embedding")
        if not isinstance(embedding, list) or len(embedding) != 384:
            return None
        try:
            return [float(value) for value in embedding]
        except (TypeError, ValueError):
            return None

    try:
        return await asyncio.to_thread(embed_text, query_text)
    except (RuntimeError, ValueError):
        return None


async def embed_and_store_chunk(
    *,
    db: AsyncSession,
    text: str,
    source_type: RagSourceType | str,
    user_id=None,
    disease_tag: str | None = None,
) -> RagChunk:
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("text must be a non-empty string")

    embedding = await asyncio.to_thread(embed_text, cleaned)
    if len(embedding) != EMBEDDING_DIMENSIONS:
        raise ValueError("embedding dimension mismatch")

    chunk = RagChunk(
        source="api",
        source_type=RagSourceType(source_type),
        chunk_text=cleaned,
        embedding=embedding,
        user_id=user_id,
        disease_tag=disease_tag,
        metadata_={},
    )
    db.add(chunk)
    try:
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise
    await db.refresh(chunk)
    return chunk


def _build_terms(*, question: str | None, nutrition: NutritionData) -> list[str]:
    terms: list[str] = []
    if question:
        terms.extend(
            token.lower()
            for token in re.findall(r"[a-zA-Z]{4,}", question)
            if token.lower() not in {"this", "that", "with", "from"}
        )
    if nutrition.sugar_g is not None:
        terms.append("sugar")
    if nutrition.sodium_mg is not None:
        terms.append("sodium")
    if nutrition.protein_g is not None:
        terms.append("protein")
    return list(dict.fromkeys(terms))[:8]


def _query_text(*, question: str | None, nutrition: NutritionData) -> str:
    parts = [question or ""]
    for label, value in {
        "sugar": nutrition.sugar_g,
        "sodium": nutrition.sodium_mg,
        "protein": nutrition.protein_g,
        "calories": nutrition.calories,
    }.items():
        if value is not None:
            parts.append(f"{label} {value}")
    return " ".join(part for part in parts if part).strip()
