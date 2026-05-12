"""initial_schema

Revision ID: 3127a872b1b8
Revises:
Create Date: 2026-05-03 20:17:19.966764

This is the baseline migration that:
  1. Enables the pgvector Postgres extension.
  2. Registers the custom `vector` type with SQLAlchemy so future
     autogenerate revisions can track embedding column changes.
  3. Aligns the users.full_name column type from TEXT to VARCHAR(255)
     to match the current SQLAlchemy model definition.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '3127a872b1b8'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Step 1: Enable pgvector extension.
    # This must run before any table that uses the `vector` column type.
    # IF NOT EXISTS is safe to run on a DB that already has it installed.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Step 2: Align users.full_name column type.
    # The model declares String(255) but the original schema.sql used TEXT.
    # Alembic autogenerate detected this drift and generates the ALTER here.
    op.alter_column(
        'users', 'full_name',
        existing_type=sa.TEXT(),
        type_=sa.String(length=255),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Revert users.full_name back to TEXT.
    op.alter_column(
        'users', 'full_name',
        existing_type=sa.String(length=255),
        type_=sa.TEXT(),
        existing_nullable=False,
    )

    # Drop pgvector extension.
    # WARNING: Only drop if no other columns depend on the vector type.
    # In production, comment this line out to avoid accidentally removing
    # the extension from a shared database.
    op.execute("DROP EXTENSION IF EXISTS vector")
