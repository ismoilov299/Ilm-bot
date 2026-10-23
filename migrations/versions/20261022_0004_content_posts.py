"""Private web content catalog.

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "content_posts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("channel", sa.String(255), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False, server_default=""),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("mime_type", sa.String(127)),
        sa.Column("file_name", sa.Text()),
        sa.Column("file_size", sa.BigInteger()),
        sa.Column("duration", sa.Integer()),
        sa.Column("storage_key", sa.String(64)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("channel", "message_id"),
    )


def downgrade() -> None:
    op.drop_table("content_posts")
