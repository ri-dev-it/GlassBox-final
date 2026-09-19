"""add admin review fields

Revision ID: h420260919
Revises: g420260919
"""
from alembic import op
import sqlalchemy as sa

revision = "h420260919"
down_revision = "g420260919"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("applications", sa.Column("admin_decision", sa.String(length=20), nullable=True))
    op.add_column("applications", sa.Column("admin_decided_by", sa.Integer(), nullable=True))
    op.add_column("applications", sa.Column("admin_decided_at", sa.DateTime(), nullable=True))
    op.create_foreign_key(
        "fk_applications_admin_decided_by_users",
        "applications",
        "users",
        ["admin_decided_by"],
        ["id"],
    )


def downgrade():
    op.drop_constraint("fk_applications_admin_decided_by_users", "applications", type_="foreignkey")
    op.drop_column("applications", "admin_decided_at")
    op.drop_column("applications", "admin_decided_by")
    op.drop_column("applications", "admin_decision")