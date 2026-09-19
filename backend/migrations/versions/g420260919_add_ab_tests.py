"""add A/B testing tables

Revision ID: g420260919
Revises: f320260919
"""
from alembic import op
import sqlalchemy as sa

revision = "g420260919"
down_revision = "f320260919"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ab_tests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("model_name", sa.String(50), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("control_version_id", sa.Integer(), sa.ForeignKey("model_versions.id"), nullable=False),
        sa.Column("treatment_version_id", sa.Integer(), sa.ForeignKey("model_versions.id"), nullable=False),
        sa.Column("traffic_percentage", sa.Float(), nullable=False, server_default="50"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ab_tests_model_name", "ab_tests", ["model_name"])
    op.create_index("ix_ab_tests_status", "ab_tests", ["status"])
    op.create_table(
        "ab_test_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ab_test_id", sa.Integer(), sa.ForeignKey("ab_tests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("prediction_id", sa.Integer(), sa.ForeignKey("predictions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("variant", sa.String(20), nullable=False),
        sa.Column("model_version_id", sa.Integer(), sa.ForeignKey("model_versions.id"), nullable=False),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_ab_test_results_ab_test_id", "ab_test_results", ["ab_test_id"])
    op.create_index("ix_ab_test_results_prediction_id", "ab_test_results", ["prediction_id"])


def downgrade():
    op.drop_index("ix_ab_test_results_prediction_id", table_name="ab_test_results")
    op.drop_index("ix_ab_test_results_ab_test_id", table_name="ab_test_results")
    op.drop_table("ab_test_results")
    op.drop_index("ix_ab_tests_status", table_name="ab_tests")
    op.drop_index("ix_ab_tests_model_name", table_name="ab_tests")
    op.drop_table("ab_tests")