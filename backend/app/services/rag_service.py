import asyncio
import json
import re
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import delete, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.embeddings import EMBEDDING_DIMENSIONS, embed_text
from app.models.chat import ChatMessage, ChatSession
from app.models.enums import RagSourceType
from app.models.health_profile import HealthProfile
from app.models.rag import DiseaseKnowledgeChunk, KnowledgeChunk, RagChunk
from app.schemas.analyse import NutritionData

MAX_PROMPT_TOKENS = 3500


async def retrieve_context(
    *,
    db: AsyncSession,
    user_question: str | None,
    user_profile: HealthProfile,
    nutrition_json: NutritionData | dict | None = None,
    disease_limit: int = 6,
    memory_limit: int = 4,
    knowledge_limit: int = 6,
) -> dict[str, list[dict[str, Any]]]:
    query_text = _query_text(
        question=user_question,
        nutrition=nutrition_json,
        diseases=_profile_diseases(user_profile),
    )
    embedding = await _embed_query(query_text)

    disease_context = await _retrieve_disease_context(
        db=db,
        embedding=embedding,
        question=user_question,
        diseases=_profile_diseases(user_profile),
        limit=disease_limit,
    )
    memory_context = await _retrieve_memory_context(
        db=db,
        embedding=embedding,
        question=user_question,
        user_id=user_profile.user_id,
        limit=memory_limit,
    )
    knowledge_context = await _retrieve_knowledge_context(
        db=db,
        embedding=embedding,
        question=user_question,
        nutrition=nutrition_json,
        limit=knowledge_limit,
    )
    return {
        "disease_context": disease_context,
        "memory_context": memory_context,
        "knowledge_context": knowledge_context,
    }


def build_prompt(
    *,
    nutrition_json: NutritionData | dict | None,
    retrieved_context: dict[str, list[dict[str, Any]]],
    user_question: str | None,
    user_profile: HealthProfile,
) -> str:
    nutrition_payload = _jsonable(nutrition_json)
    profile_payload = _profile_payload(user_profile)
    budget = MAX_PROMPT_TOKENS

    header = _section(
        "ROLE AND SAFETY",
        [
            "You are a nutrition education assistant. Use the user's nutrition label, health profile, retrieved evidence, and chat memory.",
            "Give educational guidance only. Do not diagnose, prescribe, or replace a clinician.",
            "Flag urgent medical uncertainty, pregnancy concerns, kidney disease, diabetes medication, severe allergies, and abnormal symptoms as reasons to consult a qualified clinician.",
            "If evidence conflicts, prefer disease-specific safety constraints, then official WHO/FDA/ICMR evidence, then chat memory.",
        ],
    )
    question_section = _section("USER QUESTION", [user_question or "Analyse this nutrition label for my health profile."])
    profile_section = _section("USER HEALTH PROFILE", [json.dumps(profile_payload, ensure_ascii=True)])
    nutrition_section = _section("PARSED NUTRITION JSON", [json.dumps(nutrition_payload, ensure_ascii=True)])
    fixed_sections = [header, question_section, profile_section, nutrition_section]
    fixed_token_count = sum(_approx_tokens(section) for section in fixed_sections)
    budget -= fixed_token_count

    disease_section = _context_section(
        title="DISEASE DIETARY EVIDENCE",
        items=retrieved_context.get("disease_context", []),
        budget=max(250, int(budget * 0.34)),
    )
    budget -= _approx_tokens(disease_section)
    knowledge_section = _context_section(
        title="WHO/FDA/ICMR NUTRITION EVIDENCE",
        items=retrieved_context.get("knowledge_context", []),
        budget=max(250, int(budget * 0.55)),
    )
    budget -= _approx_tokens(knowledge_section)
    memory_section = _context_section(
        title="RELEVANT CHAT MEMORY",
        items=retrieved_context.get("memory_context", []),
        budget=max(150, budget),
    )

    output_contract = _section(
        "ANSWER FORMAT",
        [
            "Start with a direct answer to the user question.",
            "Explain label concerns using the parsed nutrition values and retrieved evidence.",
            "Mention disease/allergy/pregnancy-specific cautions that apply to this user.",
            "Give practical food-label guidance and safer alternatives where appropriate.",
            "State uncertainty clearly when the label or evidence is insufficient.",
        ],
    )

    prompt = "\n\n".join(
        [*fixed_sections, disease_section, knowledge_section, memory_section, output_contract]
    )
    return _truncate_to_tokens(prompt, MAX_PROMPT_TOKENS)


async def retrieve_relevant_chunks(
    *,
    db: AsyncSession,
    question: str | None,
    nutrition: NutritionData,
    limit: int = 3,
) -> list[str]:
    terms = _build_terms(question=question, nutrition=nutrition)
    query_text = _query_text(question=question, nutrition=nutrition, diseases=[])
    embedding = await _embed_query(query_text)
    if embedding:
        vector_chunks = await _retrieve_legacy_chunks_by_vector(db=db, embedding=embedding, limit=limit)
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


async def embed_and_store_chunk(
    *,
    db: AsyncSession,
    text: str,
    source_type: RagSourceType | str,
    user_id=None,
    disease_tag: str | None = None,
) -> RagChunk:
    cleaned = _clean_required_text(text)
    embedding = await asyncio.to_thread(embed_text, cleaned)
    _validate_embedding(embedding)

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


async def store_knowledge_chunks(
    *,
    db: AsyncSession,
    chunks: list[dict[str, Any]],
    replace_sources: set[str] | None = None,
) -> int:
    if replace_sources:
        await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.source.in_(replace_sources)))

    for item in chunks:
        text = _clean_required_text(item["chunk_text"])
        embedding = await asyncio.to_thread(embed_text, text)
        _validate_embedding(embedding)
        db.add(
            KnowledgeChunk(
                source=item["source"],
                source_url=item.get("source_url"),
                page_number=item.get("page_number"),
                chunk_text=text,
                embedding=embedding,
                metadata_=item.get("metadata") or {},
            )
        )
    await db.commit()
    return len(chunks)


async def store_disease_knowledge_chunks(
    *,
    db: AsyncSession,
    chunks: list[dict[str, Any]],
    replace: bool = True,
) -> int:
    if replace:
        await db.execute(delete(DiseaseKnowledgeChunk))

    for item in chunks:
        evidence_text = _clean_required_text(item["evidence_text"])
        chunk_text = _clean_required_text(item["chunk_text"])
        embedding = await asyncio.to_thread(embed_text, chunk_text)
        _validate_embedding(embedding)
        db.add(
            DiseaseKnowledgeChunk(
                disease_tag=_canonical_disease(str(item["disease_tag"])),
                rule_code=str(item["rule_code"]),
                evidence_text=evidence_text,
                chunk_text=chunk_text,
                embedding=embedding,
                metadata_=item.get("metadata") or {},
            )
        )
    await db.commit()
    return len(chunks)


async def _retrieve_disease_context(
    *,
    db: AsyncSession,
    embedding: list[float] | None,
    question: str | None,
    diseases: list[str],
    limit: int,
) -> list[dict[str, Any]]:
    if not diseases:
        return []

    canonical = [_canonical_disease(disease) for disease in diseases]
    try:
        statement = select(DiseaseKnowledgeChunk).where(DiseaseKnowledgeChunk.disease_tag.in_(canonical))
        if embedding:
            statement = statement.order_by(DiseaseKnowledgeChunk.embedding.op("<=>")(_vector_literal(embedding)))
        else:
            terms = _keyword_terms(question or " ".join(canonical))
            if terms:
                statement = statement.where(
                    or_(*[DiseaseKnowledgeChunk.chunk_text.ilike(f"%{term}%") for term in terms])
                )
            statement = statement.order_by(DiseaseKnowledgeChunk.disease_tag, DiseaseKnowledgeChunk.rule_code)
        result = await db.execute(statement.limit(limit))
    except Exception:
        return []

    return [
        {
            "text": chunk.chunk_text,
            "evidence_text": chunk.evidence_text,
            "disease_tag": chunk.disease_tag,
            "rule_code": chunk.rule_code,
            "metadata": chunk.metadata_,
        }
        for chunk in result.scalars().all()
    ]


async def _retrieve_memory_context(
    *,
    db: AsyncSession,
    embedding: list[float] | None,
    question: str | None,
    user_id: UUID,
    limit: int,
) -> list[dict[str, Any]]:
    try:
        statement = (
            select(ChatMessage, ChatSession)
            .join(ChatSession, ChatMessage.session_id == ChatSession.id)
            .where(ChatSession.user_id == user_id, ChatMessage.embedding.is_not(None))
        )
        if embedding:
            statement = statement.order_by(ChatMessage.embedding.op("<=>")(_vector_literal(embedding)))
        else:
            terms = _keyword_terms(question or "")
            if not terms:
                return []
            statement = statement.where(or_(*[ChatMessage.content.ilike(f"%{term}%") for term in terms]))
            statement = statement.order_by(ChatMessage.created_at.desc())
        result = await db.execute(statement.limit(limit))
    except Exception:
        return []

    return [
        {
            "text": message.content,
            "role": message.role.value,
            "session_id": str(session.id),
            "session_title": session.title,
            "metadata": message.metadata_,
        }
        for message, session in result.all()
    ]


async def _retrieve_knowledge_context(
    *,
    db: AsyncSession,
    embedding: list[float] | None,
    question: str | None,
    nutrition: NutritionData | dict | None,
    limit: int,
) -> list[dict[str, Any]]:
    try:
        statement = select(KnowledgeChunk)
        if embedding:
            statement = statement.order_by(KnowledgeChunk.embedding.op("<=>")(_vector_literal(embedding)))
        else:
            terms = _build_terms(question=question, nutrition=nutrition)
            if terms:
                statement = statement.where(or_(*[KnowledgeChunk.chunk_text.ilike(f"%{term}%") for term in terms]))
            statement = statement.order_by(KnowledgeChunk.created_at.desc())
        result = await db.execute(statement.limit(limit))
    except Exception:
        return []

    return [
        {
            "text": chunk.chunk_text,
            "source": chunk.source,
            "source_url": chunk.source_url,
            "page_number": chunk.page_number,
            "metadata": chunk.metadata_,
        }
        for chunk in result.scalars().all()
    ]


async def _retrieve_legacy_chunks_by_vector(*, db: AsyncSession, embedding: list[float], limit: int) -> list[str]:
    try:
        result = await db.execute(
            select(RagChunk)
            .order_by(RagChunk.embedding.op("<=>")(_vector_literal(embedding)))
            .limit(limit)
        )
    except Exception:
        return []
    return [chunk.chunk_text for chunk in result.scalars().all()]


async def _embed_query(query_text: str) -> list[float] | None:
    cleaned = query_text.strip()
    if not cleaned:
        return None

    try:
        embedding = await asyncio.to_thread(embed_text, cleaned)
        _validate_embedding(embedding)
        return embedding
    except Exception:
        return None


def _build_terms(*, question: str | None, nutrition: NutritionData | dict | None) -> list[str]:
    terms = _keyword_terms(question or "")
    nutrition_dict = _jsonable(nutrition)
    for key, term in {
        "sugar_g": "sugar",
        "sodium_mg": "sodium",
        "protein_g": "protein",
        "calories": "calories",
        "fat_g": "fat",
        "fiber_g": "fiber",
    }.items():
        if nutrition_dict.get(key) is not None:
            terms.append(term)
    return list(dict.fromkeys(terms))[:10]


def _query_text(
    *,
    question: str | None,
    nutrition: NutritionData | dict | None,
    diseases: list[str],
) -> str:
    parts = [question or ""]
    nutrition_dict = _jsonable(nutrition)
    for label in ("sugar_g", "sodium_mg", "protein_g", "calories", "fat_g", "fiber_g"):
        value = nutrition_dict.get(label)
        if value is not None:
            parts.append(f"{label.replace('_', ' ')} {value}")
    if diseases:
        parts.append("health conditions " + " ".join(diseases))
    return " ".join(part for part in parts if part).strip()


def _profile_diseases(profile: HealthProfile) -> list[str]:
    diseases = profile.diseases or []
    normalized: list[str] = []
    for disease in diseases:
        if isinstance(disease, dict):
            value = disease.get("condition") or disease.get("name") or disease.get("disease")
        else:
            value = disease
        if value:
            normalized.append(_canonical_disease(str(value)))
    return list(dict.fromkeys(normalized))


def _profile_payload(profile: HealthProfile) -> dict[str, Any]:
    return {
        "age": profile.age,
        "weight_kg": _jsonable_value(profile.weight_kg),
        "height_cm": _jsonable_value(profile.height_cm),
        "sex": profile.sex.value,
        "activity_level": profile.activity_level.value,
        "goal": profile.goal.value,
        "allergies": profile.allergies,
        "diseases": profile.diseases or [],
        "dietary_preferences": profile.dietary_preferences,
        "nutrition_goals": profile.nutrition_goals,
    }


def _context_section(title: str, items: list[dict[str, Any]], budget: int) -> str:
    if not items:
        return _section(title, ["No relevant retrieved context found."])

    lines: list[str] = []
    spent = 0
    for index, item in enumerate(items, start=1):
        source = item.get("source") or item.get("disease_tag") or item.get("session_title") or "retrieved"
        page = f", page {item['page_number']}" if item.get("page_number") else ""
        metadata = item.get("metadata") or {}
        evidence = item.get("evidence_text") or item.get("text") or ""
        line = f"{index}. [{source}{page}] {_truncate_text(evidence, 1200)}"
        if metadata.get("nutrient_focus"):
            line += f" Focus: {metadata['nutrient_focus']}."
        line_tokens = _approx_tokens(line)
        if spent + line_tokens > budget and lines:
            break
        lines.append(line)
        spent += line_tokens
    return _section(title, lines)


def _section(title: str, lines: list[str]) -> str:
    return title + "\n" + "\n".join(lines)


def _approx_tokens(text: str) -> int:
    return max(1, int(len(re.findall(r"\S+", text)) * 1.25))


def _truncate_to_tokens(text: str, max_tokens: int) -> str:
    words = re.findall(r"\S+\s*", text)
    if len(words) * 1.25 <= max_tokens:
        return text
    return "".join(words[: int(max_tokens / 1.25)]).rstrip()


def _truncate_text(text: str, max_chars: int) -> str:
    clean = " ".join(text.split())
    if len(clean) <= max_chars:
        return clean
    return clean[: max_chars - 1].rstrip() + "."


def _keyword_terms(text: str) -> list[str]:
    stop_words = {
        "this",
        "that",
        "with",
        "from",
        "have",
        "what",
        "safe",
        "label",
        "food",
        "nutrition",
    }
    return [
        token.lower()
        for token in re.findall(r"[a-zA-Z][a-zA-Z-]{3,}", text)
        if token.lower() not in stop_words
    ][:8]


def _canonical_disease(value: str) -> str:
    normalized = re.sub(r"\s+", " ", value.strip().lower().replace("_", " "))
    aliases = {
        "chronic kidney disease": "ckd",
        "kidney disease": "ckd",
        "coronary artery disease": "heart disease",
        "cardiovascular disease": "heart disease",
        "high cholesterol": "hyperlipidemia",
        "fatty liver disease": "fatty liver",
        "non alcoholic fatty liver disease": "fatty liver",
        "nafld": "fatty liver",
        "acid reflux": "gerd",
        "coeliac": "celiac",
        "polycystic ovary syndrome": "pcos",
    }
    return aliases.get(normalized, normalized)


def _jsonable(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return {key: _jsonable_value(item) for key, item in value.model_dump().items()}
    if isinstance(value, dict):
        return {key: _jsonable_value(item) for key, item in value.items()}
    return {}


def _jsonable_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, list):
        return [_jsonable_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable_value(item) for key, item in value.items()}
    return value


def _clean_required_text(text: str) -> str:
    if text is None:
        raise ValueError("text must be a non-empty string")
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("text must be a non-empty string")
    return cleaned


def _validate_embedding(embedding: list[float]) -> None:
    if len(embedding) != EMBEDDING_DIMENSIONS:
        raise ValueError("embedding dimension mismatch")


def _vector_literal(embedding: list[float]) -> str:
    return "[" + ",".join(str(float(value)) for value in embedding) + "]"
