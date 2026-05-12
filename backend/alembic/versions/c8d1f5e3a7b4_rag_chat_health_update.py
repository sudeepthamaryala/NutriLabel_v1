"""rag_chat_health_update

Revision ID: c8d1f5e3a7b4
Revises: 3127a872b1b8
Create Date: 2026-05-07 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c8d1f5e3a7b4'
down_revision: Union[str, Sequence[str], None] = '3127a872b1b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE rag_source_type AS ENUM ('knowledge', 'disease', 'user_memory', 'label_ocr');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )

    op.execute(
        "ALTER TABLE rag_chunks ADD COLUMN IF NOT EXISTS source_type rag_source_type NOT NULL DEFAULT 'knowledge'"
    )
    op.execute(
        "ALTER TABLE rag_chunks ADD COLUMN IF NOT EXISTS user_id uuid REFERENCES users(id) ON DELETE CASCADE"
    )
    op.execute("ALTER TABLE rag_chunks ADD COLUMN IF NOT EXISTS disease_tag text")
    op.execute("DROP INDEX IF EXISTS idx_rag_chunks_embedding_hnsw")
    op.execute("ALTER TABLE rag_chunks ALTER COLUMN embedding TYPE vector(384)")

    op.execute("ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS embedding vector(384)")

    op.execute(
        "ALTER TABLE health_profiles ADD COLUMN IF NOT EXISTS nutrition_goals text"
    )
    op.execute(
        "ALTER TABLE health_profiles ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now()"
    )
    op.execute(
        "ALTER TABLE health_profiles ALTER COLUMN diseases TYPE jsonb USING to_jsonb(diseases)"
    )
    op.execute("ALTER TABLE health_profiles ALTER COLUMN diseases SET DEFAULT '[]'::jsonb")
    op.execute("UPDATE health_profiles SET diseases = '[]'::jsonb WHERE diseases IS NULL")
    op.execute("ALTER TABLE health_profiles ALTER COLUMN diseases SET NOT NULL")

    op.execute("ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS label_image_url text")
    op.execute(
        "ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS parsed_nutrition_json jsonb NOT NULL DEFAULT '{}'::jsonb"
    )
    op.execute("ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS session_summary text")
    op.execute(
        "ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now()"
    )

    op.execute(
        """
        DO $$
        BEGIN
            CREATE INDEX IF NOT EXISTS idx_chat_messages_embedding_hnsw
            ON chat_messages USING hnsw (embedding vector_cosine_ops);
        EXCEPTION
            WHEN undefined_object OR feature_not_supported THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            CREATE INDEX IF NOT EXISTS idx_rag_chunks_embedding_hnsw
            ON rag_chunks USING hnsw (embedding vector_cosine_ops);
        EXCEPTION
            WHEN undefined_object OR feature_not_supported THEN NULL;
        END $$;
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_rag_chunks_source_type ON rag_chunks(source_type)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_rag_chunks_disease_tag ON rag_chunks(disease_tag)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_rag_chunks_user_id ON rag_chunks(user_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_chat_sessions_parsed_nutrition_json_gin ON chat_sessions USING gin(parsed_nutrition_json)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_chat_messages_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_rag_chunks_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_rag_chunks_source_type")
    op.execute("DROP INDEX IF EXISTS idx_rag_chunks_disease_tag")
    op.execute("DROP INDEX IF EXISTS idx_rag_chunks_user_id")
    op.execute("DROP INDEX IF EXISTS idx_chat_sessions_parsed_nutrition_json_gin")

    op.execute("ALTER TABLE chat_sessions DROP COLUMN IF EXISTS session_summary")
    op.execute("ALTER TABLE chat_sessions DROP COLUMN IF EXISTS parsed_nutrition_json")
    op.execute("ALTER TABLE chat_sessions DROP COLUMN IF EXISTS label_image_url")

    op.execute("ALTER TABLE health_profiles DROP COLUMN IF EXISTS nutrition_goals")
    op.execute("ALTER TABLE health_profiles DROP COLUMN IF EXISTS updated_at")
    op.execute(
        "ALTER TABLE health_profiles ALTER COLUMN diseases TYPE text[] USING ARRAY(SELECT jsonb_array_elements_text(diseases))"
    )
    op.execute("ALTER TABLE health_profiles ALTER COLUMN diseases SET DEFAULT '{}'::text[]")

    op.execute("ALTER TABLE chat_messages DROP COLUMN IF EXISTS embedding")

    op.execute("ALTER TABLE rag_chunks DROP COLUMN IF EXISTS disease_tag")
    op.execute("ALTER TABLE rag_chunks DROP COLUMN IF EXISTS user_id")
    op.execute("ALTER TABLE rag_chunks DROP COLUMN IF EXISTS source_type")
    op.execute("ALTER TABLE rag_chunks ALTER COLUMN embedding TYPE vector(1536)")
    op.execute("DROP TYPE IF EXISTS rag_source_type")
