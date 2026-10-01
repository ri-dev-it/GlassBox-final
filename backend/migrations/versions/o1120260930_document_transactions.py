"""Normalized bank statement transactions."""

from alembic import op
import sqlalchemy as sa

revision = "o1120260930"
down_revision = "n1020260930"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "document_transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("debit", sa.Numeric(16, 2), nullable=False),
        sa.Column("credit", sa.Numeric(16, 2), nullable=False),
        sa.Column("balance", sa.Numeric(16, 2), nullable=False),
        sa.UniqueConstraint(
            "document_id", "sequence", name="uq_document_transaction_sequence"
        ),
    )
    op.create_index(
        "ix_document_transactions_document_id",
        "document_transactions",
        ["document_id"],
    )


def downgrade():
    op.drop_table("document_transactions")
