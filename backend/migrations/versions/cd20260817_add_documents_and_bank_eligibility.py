"""add document verification and bank eligibility records

Revision ID: cd20260817
Revises: bc20260814
"""

from alembic import op
import sqlalchemy as sa

revision = "cd20260817"
down_revision = "bc20260814"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=True),
        sa.Column("document_type", sa.String(40), nullable=False),
        sa.Column(
            "storage_reference", sa.String(512), nullable=False, unique=True
        ),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"]),
    )
    op.create_index("ix_documents_user_id", "documents", ["user_id"])
    op.create_index(
        "ix_documents_application_id", "documents", ["application_id"]
    )
    op.create_table(
        "document_verifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("extracted_information_json", sa.Text(), nullable=False),
        sa.Column("mismatches_json", sa.Text(), nullable=False),
        sa.Column("verification_message", sa.String(1000), nullable=False),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
    )
    op.create_index(
        "ix_document_verifications_document_id",
        "document_verifications",
        ["document_id"],
    )
    op.create_table(
        "bank_eligibility_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("bank_name", sa.String(100), nullable=False),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("reasons_json", sa.Text(), nullable=False),
        sa.Column("conditions_json", sa.Text(), nullable=False),
        sa.Column("risk_indicators_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"]),
    )
    op.create_index(
        "ix_bank_eligibility_results_application_id",
        "bank_eligibility_results",
        ["application_id"],
    )


def downgrade():
    op.drop_table("bank_eligibility_results")
    op.drop_table("document_verifications")
    op.drop_table("documents")
