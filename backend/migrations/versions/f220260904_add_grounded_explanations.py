"""persist grounded SHAP explanations

Revision ID: f220260904
Revises: f120260904
"""

from alembic import op
import sqlalchemy as sa

revision = "f220260904"
down_revision = "f120260904"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "grounded_explanations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("application_id", sa.Integer(), nullable=True),
        sa.Column("merchant_id", sa.String(100), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("grounded_in_json", sa.Text(), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"]),
        sa.UniqueConstraint("application_id"),
        sa.UniqueConstraint("merchant_id"),
    )
    op.create_index(
        "ix_grounded_explanations_application_id",
        "grounded_explanations",
        ["application_id"],
        unique=True,
    )
    op.create_index(
        "ix_grounded_explanations_merchant_id",
        "grounded_explanations",
        ["merchant_id"],
        unique=True,
    )


def downgrade():
    op.drop_index(
        "ix_grounded_explanations_merchant_id",
        table_name="grounded_explanations",
    )
    op.drop_index(
        "ix_grounded_explanations_application_id",
        table_name="grounded_explanations",
    )
    op.drop_table("grounded_explanations")
