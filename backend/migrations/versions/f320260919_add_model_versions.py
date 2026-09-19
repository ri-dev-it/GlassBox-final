"""add model version registry

Revision ID: f320260919
Revises: f220260904
"""
from alembic import op
import sqlalchemy as sa

revision = "f320260919"
down_revision = "f220260904"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "model_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("model_name", sa.String(50), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("trained_at", sa.DateTime(), nullable=False),
        sa.Column("file_path", sa.String(512), nullable=False),
        sa.Column("metrics_json", sa.Text(), nullable=False),
        sa.Column("governance_passed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("model_name", "version_number", name="uq_model_versions_name_number"),
    )
    op.create_index("ix_model_versions_model_name", "model_versions", ["model_name"])
    op.create_index("ix_model_versions_is_active", "model_versions", ["is_active"])


def downgrade():
    op.drop_index("ix_model_versions_is_active", table_name="model_versions")
    op.drop_index("ix_model_versions_model_name", table_name="model_versions")
    op.drop_table("model_versions")