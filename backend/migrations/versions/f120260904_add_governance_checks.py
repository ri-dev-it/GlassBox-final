"""persist fairness governance decisions

Revision ID: f120260904
Revises: f020260904
"""

from alembic import op
import sqlalchemy as sa

revision = "f120260904"
down_revision = "f020260904"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "governance_checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("model_key", sa.String(100), nullable=False),
        sa.Column("model_version", sa.String(100), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("failed_checks_json", sa.Text(), nullable=False),
        sa.Column("checked_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_governance_checks_model_key", "governance_checks", ["model_key"]
    )


def downgrade():
    op.drop_index(
        "ix_governance_checks_model_key", table_name="governance_checks"
    )
    op.drop_table("governance_checks")
