"""add functional unique index on lower(sku)

Revision ID: base002
Revises: base001
Create Date: 2025-01-02 00:00:00
"""
from alembic import op

revision = "base002"
down_revision = "base001"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_products_lower_sku "
        "ON products (LOWER(sku));"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS ux_products_lower_sku;")
