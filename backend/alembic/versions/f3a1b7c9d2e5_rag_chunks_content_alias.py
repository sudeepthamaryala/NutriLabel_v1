"""rag_chunks content compatibility alias

Revision ID: f3a1b7c9d2e5
Revises: c8d1f5e3a7b4
Create Date: 2026-05-13 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "f3a1b7c9d2e5"
down_revision: Union[str, Sequence[str], None] = "c8d1f5e3a7b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE rag_chunks ADD COLUMN IF NOT EXISTS content text GENERATED ALWAYS AS (chunk_text) STORED"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE rag_chunks DROP COLUMN IF EXISTS content")
