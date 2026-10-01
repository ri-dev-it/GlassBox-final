"""add public application id

Revision ID: bc20260814
Revises: ae113030d130
"""

from alembic import op
import sqlalchemy as sa

revision = "bc20260814"
down_revision = "ae113030d130"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "applications",
        sa.Column("public_id", sa.String(length=20), nullable=True),
    )
    op.create_index(
        "ix_applications_public_id", "applications", ["public_id"], unique=True
    )


def downgrade():
    op.drop_index("ix_applications_public_id", table_name="applications")
    op.drop_column("applications", "public_id")
