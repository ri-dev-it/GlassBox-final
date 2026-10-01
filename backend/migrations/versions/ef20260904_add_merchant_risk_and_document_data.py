"""persist merchant risk surfaces and simulated document checks

Revision ID: ef20260904
Revises: cd20260817
"""

from alembic import op
import sqlalchemy as sa

revision = "ef20260904"
down_revision = "cd20260817"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "merchant_transaction_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("merchant_id", sa.String(100), nullable=False, unique=True),
        sa.Column("gmv_trend_30d", sa.Float(), nullable=False),
        sa.Column("gmv_trend_90d", sa.Float(), nullable=False),
        sa.Column("payment_success_rate", sa.Float(), nullable=False),
        sa.Column("refund_rate", sa.Float(), nullable=False),
        sa.Column("chargeback_rate", sa.Float(), nullable=False),
        sa.Column("customer_concentration", sa.Float(), nullable=False),
        sa.Column("order_volume_volatility", sa.Float(), nullable=False),
        sa.Column("account_age_days", sa.Float(), nullable=False),
        sa.Column("actual_monthly_gmv", sa.Float(), nullable=False),
        sa.Column("actual_monthly_inflow", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_merchant_transaction_profiles_merchant_id",
        "merchant_transaction_profiles",
        ["merchant_id"],
        unique=True,
    )
    op.create_table(
        "merchant_transaction_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("merchant_id", sa.String(100), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("gmv", sa.Float(), nullable=False),
        sa.Column("refund_count", sa.Integer(), nullable=False),
        sa.Column("chargeback_count", sa.Integer(), nullable=False),
        sa.Column("order_count", sa.Integer(), nullable=False),
    )
    op.create_index(
        "ix_merchant_transaction_history_merchant_id",
        "merchant_transaction_history",
        ["merchant_id"],
    )
    op.create_table(
        "merchant_fraud_checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("merchant_id", sa.String(100), nullable=False),
        sa.Column("fraud_score", sa.Float(), nullable=False),
        sa.Column("flags_json", sa.Text(), nullable=False),
        sa.Column("flagged_days_json", sa.Text(), nullable=False),
        sa.Column("checked_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_merchant_fraud_checks_merchant_id",
        "merchant_fraud_checks",
        ["merchant_id"],
    )
    op.create_table(
        "merchant_tier_assessments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("merchant_id", sa.String(100), nullable=False),
        sa.Column("current_tier", sa.String(100), nullable=True),
        sa.Column("next_tier", sa.String(100), nullable=True),
        sa.Column("results_json", sa.Text(), nullable=False),
        sa.Column("assessed_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_merchant_tier_assessments_merchant_id",
        "merchant_tier_assessments",
        ["merchant_id"],
    )
    op.create_table(
        "portfolio_exposure_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tier_summary_json", sa.Text(), nullable=False),
        sa.Column("blocking_signals_json", sa.Text(), nullable=False),
        sa.Column("total_merchants", sa.Integer(), nullable=False),
        sa.Column("total_estimated_exposure", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "merchant_document_verifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("merchant_id", sa.String(100), nullable=False, unique=True),
        sa.Column("gst_reported_monthly_revenue", sa.Float(), nullable=False),
        sa.Column("bank_statement_avg_balance", sa.Float(), nullable=False),
        sa.Column("bank_statement_monthly_inflow", sa.Float(), nullable=False),
        sa.Column("consistent", sa.Boolean(), nullable=False),
        sa.Column("mismatches_json", sa.Text(), nullable=False),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_merchant_document_verifications_merchant_id",
        "merchant_document_verifications",
        ["merchant_id"],
        unique=True,
    )


def downgrade():
    op.drop_table("merchant_document_verifications")
    op.drop_table("portfolio_exposure_snapshots")
    op.drop_index(
        "ix_merchant_tier_assessments_merchant_id",
        table_name="merchant_tier_assessments",
    )
    op.drop_table("merchant_tier_assessments")
    op.drop_index(
        "ix_merchant_fraud_checks_merchant_id",
        table_name="merchant_fraud_checks",
    )
    op.drop_table("merchant_fraud_checks")
    op.drop_index(
        "ix_merchant_transaction_history_merchant_id",
        table_name="merchant_transaction_history",
    )
    op.drop_table("merchant_transaction_history")
    op.drop_index(
        "ix_merchant_transaction_profiles_merchant_id",
        table_name="merchant_transaction_profiles",
    )
    op.drop_table("merchant_transaction_profiles")
