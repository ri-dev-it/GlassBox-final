"""add per-document human review and loan type"""
from alembic import op
import sqlalchemy as sa

revision = "i520260923"
down_revision = "h420260919"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("applications", sa.Column("loan_type", sa.String(length=40), nullable=False, server_default="PERSONAL_LOAN"))
    op.add_column("documents", sa.Column("document_status", sa.String(length=20), nullable=False, server_default="pending"))
    op.add_column("documents", sa.Column("reviewed_by", sa.Integer(), nullable=True))
    op.add_column("documents", sa.Column("reviewed_at", sa.DateTime(), nullable=True))
    op.create_foreign_key("fk_documents_reviewed_by", "documents", "users", ["reviewed_by"], ["id"])

def downgrade():
    op.drop_constraint("fk_documents_reviewed_by", "documents", type_="foreignkey")
    op.drop_column("documents", "reviewed_at")
    op.drop_column("documents", "reviewed_by")
    op.drop_column("documents", "document_status")
    op.drop_column("applications", "loan_type")
