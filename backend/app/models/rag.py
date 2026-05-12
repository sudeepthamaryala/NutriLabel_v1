"""
RagChunk — pgvector-backed knowledge store for NutriLens RAG pipeline.

Design rationale
────────────────
Each row is one "chunk" of text that has been semantically embedded.
During inference, the backend embeds the user's question, then runs a
cosine-similarity search (via pgvector's <=> operator) to find the
top-k most relevant chunks, which are injected into the LLM prompt.

Why vector(384)?
  all-MiniLM-L6-v2 produces 384-dimensional embeddings.  This is the
  sweet spot for CPU-deployable RAG:
    • OpenAI text-embedding-3-small → 1536 dims → 6× more RAM + storage
    • all-MiniLM-L6-v2 → 384 dims → <90 MB model, ~0.5 ms/sentence CPU
  For a nutrition knowledge base of a few thousand chunks the quality
  difference is negligible; the speed and cost difference is enormous.

source_type enum drives retrieval scoping
  Instead of a single similarity search over ALL chunks (which would
  mix user-private memory with public nutrition knowledge), the retrieval
  layer filters by source_type first, then ranks by vector distance.
  See RagSourceType docstring in enums.py for full reasoning.

user_id FK (nullable)
  Only set when source_type = 'user_memory'.  Enforces row-level
  isolation: user A can never retrieve user B's memory chunks.
  NULL for public knowledge and disease chunks.

disease_tag (nullable)
  Only set when source_type = 'disease'.  Allows:
      WHERE source_type = 'disease' AND disease_tag = 'diabetes'
  so a diabetic user gets targeted dietary rules without cluttering
  prompts for healthy users.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import RagSourceType
from app.models.types import Vector


class RagChunk(Base):
    __tablename__ = "rag_chunks"
    __table_args__ = (
        # Sanity guards: refuse blank text rows — they'd produce meaningless embeddings
        CheckConstraint("length(trim(chunk_text)) > 0", name="rag_chunks_text_not_blank"),
        # Fast lookup by source_type for retrieval-layer pre-filtering
        Index("idx_rag_chunks_source_type", "source_type"),
        # Combined index: filter disease chunks by tag, then rank by vector distance
        Index("idx_rag_chunks_disease_tag", "disease_tag"),
        # Per-user memory retrieval: isolate user_memory chunks to their owner
        Index("idx_rag_chunks_user_id", "user_id"),
        # GIN on metadata for future JSONB querying (e.g. page number, section)
        Index("idx_rag_chunks_metadata_gin", "metadata", postgresql_using="gin"),
        # HNSW vector index for approximate nearest-neighbour cosine search.
        # HNSW is faster than IVFFlat for small-to-medium knowledge bases
        # and does NOT require a training step (IVFFlat needs VACUUM + index build
        # after data load).  m=16, ef_construction=64 are good defaults for
        # <100k rows; bump ef_construction to 128 for >100k rows.
        # vector_cosine_ops → cosine similarity (normalised vectors, direction-only).
        Index(
            "idx_rag_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
            postgresql_with={"m": 16, "ef_construction": 64},
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )

    # ── Source classification ─────────────────────────────────────────────────
    source_type: Mapped[RagSourceType] = mapped_column(
        Enum(
            RagSourceType,
            name="rag_source_type",
            values_callable=lambda e: [item.value for item in e],
        ),
        nullable=False,
        # Default to 'knowledge' so existing ingestion scripts keep working
        # until they are updated to pass an explicit source_type.
        server_default="knowledge",
    )
    # Human-readable label: e.g. "WHO 2023 Nutrition Guidelines", "FSSAI Label Rules"
    source: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Content ───────────────────────────────────────────────────────────────
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)

    # 384 dims — matches all-MiniLM-L6-v2 output dimensionality.
    # NOT NULL: every chunk must be embedded before storage so that
    # the similarity search index stays consistent.
    embedding: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)

    # Arbitrary structured metadata: page numbers, section headers, confidence
    # scores, ingestion timestamps — anything useful for re-ranking or citation.
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    # ── Personalisation / disease scoping ────────────────────────────────────
    # FK to users.id — only set for source_type = 'user_memory'.
    # ON DELETE CASCADE: if a user account is deleted, their private memory
    # chunks are automatically removed (GDPR hygiene).
    user_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Free-text disease tag: "diabetes", "hypertension", "celiac", etc.
    # Kept as TEXT (not FK to a diseases table) to stay lightweight and
    # avoid premature normalisation for an academic project.
    disease_tag: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    # Lazy reference back to the user who owns this memory chunk.
    # viewonly=True: we never cascade writes through this relationship.
    user: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[user_id],
        viewonly=True,
    )
