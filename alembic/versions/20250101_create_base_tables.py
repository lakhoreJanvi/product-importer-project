"""create base tables

Revision ID: base001
Revises:
Create Date: 2025-01-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "base001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "products",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("sku", sa.String(255), nullable=False),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("price", sa.String(64)),
        sa.Column("active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime),
        sa.Column("updated_at", sa.DateTime),
    )

    op.create_table(
        "webhooks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("enabled", sa.Boolean, server_default="true"),
    )

    op.create_table(
        "import_jobs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("total_rows", sa.Integer, server_default="0"),
        sa.Column("processed_rows", sa.Integer, server_default="0"),
        sa.Column("status", sa.String(64), server_default="pending"),
        sa.Column("error", sa.Text),
        sa.Column("created_at", sa.DateTime),
        sa.Column("updated_at", sa.DateTime),
    )


def downgrade():
    op.drop_table("import_jobs")
    op.drop_table("webhooks")
    op.drop_table("products")
