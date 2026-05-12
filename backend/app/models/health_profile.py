"""
HealthProfile — per-user biometric and dietary profile.

Design rationale for diseases: JSONB vs TEXT[]
───────────────────────────────────────────────
Old schema:  diseases TEXT[]   e.g. ['diabetes', 'hypertension']
New schema:  diseases JSONB    e.g. [{"condition": "diabetes", "severity": "type2"},
                                      {"condition": "hypertension", "severity": "stage1"}]

Why JSONB is better:
  1. Structured severity data — knowing *which type* of diabetes changes
     which dietary rules to retrieve.  TEXT[] can only store the name,
     not the sub-classification.

  2. Future extensibility — you can add keys ("diagnosed_year", "controlled")
     without a schema migration.  Adding a column to TEXT[] is impossible.

  3. JSONB queries — PostgreSQL can filter and index JSONB:
       WHERE diseases @> '[{"condition": "diabetes"}]'
     This makes disease-aware RAG retrieval queries far more expressive
     than ARRAY operations.

  4. Frontend / API friendliness — Flutter receives a typed JSON list
     instead of a raw array of strings, making it easier to render disease
     cards with severity badges.

nutrition_goals: TEXT (not JSONB, not ARRAY)
────────────────────────────────────────────
  A single free-text field lets users and the registration form express
  nuanced goals like "reduce belly fat, maintain energy for gym sessions".
  This is injected verbatim into the LLM prompt — the model understands
  natural language better than a structured enum here.
  Future: can be vectorised and stored in rag_chunks as 'user_memory'.

Fields that should NEVER become embeddings:
───────────────────────────────────────────
  • age, weight_kg, height_cm  — raw numbers, not semantic text
  • sex, activity_level, goal  — small enums, trivial lookup
  • allergies                  — exact-match filtering, not semantic search
  • email / id                 — PII, never expose to vector search

  Only 'nutrition_goals' and summarised 'diseases' text are suitable
  for embedding because they carry semantic meaning for RAG retrieval.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, Numeric, Text, func, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TEXT, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import ActivityLevel, HealthGoal, Sex


class HealthProfile(Base):
    __tablename__ = "health_profiles"
    __table_args__ = (
        CheckConstraint("age between 1 and 120", name="health_profiles_age_range"),
        CheckConstraint("weight_kg > 0 and weight_kg <= 500", name="health_profiles_weight_range"),
        CheckConstraint("height_cm > 0 and height_cm <= 300", name="health_profiles_height_range"),
    )

    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # ── Biometrics ────────────────────────────────────────────────────────────
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    height_cm: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    sex: Mapped[Sex] = mapped_column(
        Enum(Sex, name="sex", values_callable=lambda enum: [item.value for item in enum]),
        nullable=False,
    )
    activity_level: Mapped[ActivityLevel] = mapped_column(
        Enum(
            ActivityLevel,
            name="activity_level",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
    )
    goal: Mapped[HealthGoal] = mapped_column(
        Enum(
            HealthGoal,
            name="health_goal",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
    )

    # ── Dietary restrictions ──────────────────────────────────────────────────
    allergies: Mapped[list[str]] = mapped_column(
        ARRAY(TEXT),
        nullable=False,
        default=list,
        server_default=text("'{}'::text[]"),
    )
    dietary_preferences: Mapped[list[str]] = mapped_column(
        ARRAY(TEXT),
        nullable=False,
        default=list,
        server_default=text("'{}'::text[]"),
    )

    # ── Disease tracking (JSONB) ──────────────────────────────────────────────
    # Replaces the old TEXT[] diseases column.
    # Expected schema:
    #   [
    #     {"condition": "diabetes",     "severity": "type2"},
    #     {"condition": "hypertension", "severity": "stage1"}
    #   ]
    # 'condition' is the canonical disease name used to match disease_tag
    # in rag_chunks for targeted retrieval.
    # 'severity' is optional sub-classification; omit or set to "unknown"
    # if not applicable.
    diseases: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
        server_default=text("'[]'::jsonb"),
    )

    # ── Personalisation ───────────────────────────────────────────────────────
    # Free-text nutrition goals set by the user.
    # Example: "reduce sugar, build muscle, stay under 2000 kcal/day"
    # Injected into LLM prompt as-is.  Future: embed and store as user_memory.
    nutrition_goals: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(back_populates="health_profile")
