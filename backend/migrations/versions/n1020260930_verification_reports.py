"""Persist immutable overall verification snapshots."""
from alembic import op
import sqlalchemy as sa

revision = "n1020260930"
down_revision = "m920260930"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("verification_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("application_id", sa.Integer(), sa.ForeignKey("applications.id")),
        sa.Column("verdict", sa.String(20), nullable=False),
        sa.Column("report_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False))
    for column in ("user_id", "application_id"):
        op.create_index(f"ix_verification_reports_{column}", "verification_reports", [column])


def downgrade():
    op.drop_table("verification_reports")
