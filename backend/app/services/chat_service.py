import asyncio
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.embeddings import embed_text
from app.models.chat import ChatMessage, ChatSession
from app.models.enums import ChatRole, ChatSessionType


async def create_analyse_session(
    *,
    db: AsyncSession,
    user_id: UUID,
    question: str | None,
    user_content: str,
    assistant_content: str,
    metadata: dict,
    image_url: str | None = None,
) -> ChatSession:
    try:
        title = _title_from_question(question)
        session = ChatSession(user_id=user_id, type=ChatSessionType.analyse, title=title)
        db.add(session)
        await db.flush()

        db.add(
            ChatMessage(
                session_id=session.id,
                role=ChatRole.user,
                content=user_content,
                image_url=image_url,
                embedding=await _embed_message(user_content),
                metadata_={"question": question, "filename": metadata.get("filename")},
            )
        )
        db.add(
            ChatMessage(
                session_id=session.id,
                role=ChatRole.assistant,
                content=assistant_content,
                embedding=await _embed_message(assistant_content),
                metadata_=metadata,
            )
        )
        await db.commit()
        await db.refresh(session)
        return session
    except SQLAlchemyError:
        await db.rollback()
        raise


async def create_compare_session(
    *,
    db: AsyncSession,
    user_id: UUID,
    question: str | None,
    user_content: str,
    assistant_content: str,
    metadata: dict,
) -> ChatSession:
    try:
        title = _title_from_question(question) if question else "Product comparison"
        session = ChatSession(user_id=user_id, type=ChatSessionType.compare, title=title)
        db.add(session)
        await db.flush()

        db.add(
            ChatMessage(
                session_id=session.id,
                role=ChatRole.user,
                content=user_content,
                embedding=await _embed_message(user_content),
                metadata_={"question": question, "image_count": metadata.get("image_count")},
            )
        )
        db.add(
            ChatMessage(
                session_id=session.id,
                role=ChatRole.assistant,
                content=assistant_content,
                embedding=await _embed_message(assistant_content),
                metadata_=metadata,
            )
        )
        await db.commit()
        await db.refresh(session)
        return session
    except SQLAlchemyError:
        await db.rollback()
        raise


def _title_from_question(question: str | None) -> str:
    if question and question.strip():
        return question.strip()[:80]
    return "Image analysis"


async def _embed_message(content: str) -> list[float] | None:
    try:
        return await asyncio.to_thread(embed_text, content)
    except Exception:
        return None
