"""Private document extraction and append-only verification audit."""

from alembic import op
import sqlalchemy as sa

revision = "m920260930"
down_revision = "l820260927"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "document_audits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id"),
            nullable=False,
        ),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("aadhaar_hash", sa.String(64)),
        sa.Column("slot", sa.String(40), nullable=False),
        sa.Column("fields_json", sa.Text(), nullable=False),
        sa.Column("checks_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    for column in ("document_id", "user_id", "file_hash", "aadhaar_hash"):
        op.create_index(
            f"ix_document_audits_{column}", "document_audits", [column]
        )


def downgrade():
    op.drop_table("document_audits")
