"""week3 rag knowledge tables

Revision ID: 7b9c2d4e6f10
Revises: f3a1b7c9d2e5
Create Date: 2026-05-13 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "7b9c2d4e6f10"
down_revision: Union[str, Sequence[str], None] = "f3a1b7c9d2e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS knowledge_chunks (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          source text NOT NULL,
          source_url text,
          page_number integer,
          chunk_text text NOT NULL,
          embedding vector(384) NOT NULL,
          metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT knowledge_chunks_source_not_blank CHECK (length(trim(source)) > 0),
          CONSTRAINT knowledge_chunks_text_not_blank CHECK (length(trim(chunk_text)) > 0)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS disease_knowledge_chunks (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          disease_tag text NOT NULL,
          rule_code text NOT NULL,
          evidence_text text NOT NULL,
          chunk_text text NOT NULL,
          embedding vector(384) NOT NULL,
          metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT disease_knowledge_chunks_disease_not_blank CHECK (length(trim(disease_tag)) > 0),
          CONSTRAINT disease_knowledge_chunks_evidence_not_blank CHECK (length(trim(evidence_text)) > 0)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_source ON knowledge_chunks(source)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_metadata_gin ON knowledge_chunks USING gin(metadata)")
    op.execute(
        """
        DO $$
        BEGIN
            CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_embedding_hnsw
            ON knowledge_chunks USING hnsw (embedding vector_cosine_ops);
        EXCEPTION
            WHEN undefined_object OR feature_not_supported THEN NULL;
        END $$;
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_disease_knowledge_chunks_disease_tag ON disease_knowledge_chunks(disease_tag)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_disease_knowledge_chunks_metadata_gin ON disease_knowledge_chunks USING gin(metadata)"
    )
    op.execute(
        """
        DO $$
        BEGIN
            CREATE INDEX IF NOT EXISTS idx_disease_knowledge_chunks_embedding_hnsw
            ON disease_knowledge_chunks USING hnsw (embedding vector_cosine_ops);
        EXCEPTION
            WHEN undefined_object OR feature_not_supported THEN NULL;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_disease_knowledge_chunks_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_disease_knowledge_chunks_metadata_gin")
    op.execute("DROP INDEX IF EXISTS idx_disease_knowledge_chunks_disease_tag")
    op.execute("DROP INDEX IF EXISTS idx_knowledge_chunks_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_knowledge_chunks_metadata_gin")
    op.execute("DROP INDEX IF EXISTS idx_knowledge_chunks_source")
    op.execute("DROP TABLE IF EXISTS disease_knowledge_chunks")
    op.execute("DROP TABLE IF EXISTS knowledge_chunks")
