"""persist held-out metrics for both model artifacts

Revision ID: f020260904
Revises: ef20260904
"""

from alembic import op
import sqlalchemy as sa

revision = "f020260904"
down_revision = "ef20260904"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "model_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("model_key", sa.String(100), nullable=False),
        sa.Column("model_version", sa.String(100), nullable=False),
        sa.Column("precision", sa.Float(), nullable=False),
        sa.Column("recall", sa.Float(), nullable=False),
        sa.Column("f1", sa.Float(), nullable=False),
        sa.Column("roc_auc", sa.Float(), nullable=False),
        sa.Column("dataset_size", sa.Integer(), nullable=True),
        sa.Column("test_size", sa.Integer(), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_model_metrics_model_key", "model_metrics", ["model_key"]
    )


def downgrade():
    op.drop_index("ix_model_metrics_model_key", table_name="model_metrics")
    op.drop_table("model_metrics")
