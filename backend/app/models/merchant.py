import datetime
import json

from app.extensions import db


class MerchantTransactionProfile(db.Model):
    __tablename__ = "merchant_transaction_profiles"

    id = db.Column(db.Integer, primary_key=True)
    merchant_id = db.Column(
        db.String(100), nullable=False, unique=True, index=True
    )
    gmv_trend_30d = db.Column(db.Float, nullable=False)
    gmv_trend_90d = db.Column(db.Float, nullable=False)
    payment_success_rate = db.Column(db.Float, nullable=False)
    refund_rate = db.Column(db.Float, nullable=False)
    chargeback_rate = db.Column(db.Float, nullable=False)
    customer_concentration = db.Column(db.Float, nullable=False)
    order_volume_volatility = db.Column(db.Float, nullable=False)
    account_age_days = db.Column(db.Float, nullable=False)
    actual_monthly_gmv = db.Column(db.Float, nullable=False)
    actual_monthly_inflow = db.Column(db.Float, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    def feature_dict(self) -> dict:
        return {
            column: getattr(self, column)
            for column in (
                "gmv_trend_30d",
                "gmv_trend_90d",
                "payment_success_rate",
                "refund_rate",
                "chargeback_rate",
                "customer_concentration",
                "order_volume_volatility",
                "account_age_days",
            )
        }


class MerchantTransactionDay(db.Model):
    __tablename__ = "merchant_transaction_history"

    id = db.Column(db.Integer, primary_key=True)
    merchant_id = db.Column(db.String(100), nullable=False, index=True)
    transaction_date = db.Column(db.Date, nullable=False)
    gmv = db.Column(db.Float, nullable=False)
    refund_count = db.Column(db.Integer, nullable=False, default=0)
    chargeback_count = db.Column(db.Integer, nullable=False, default=0)
    order_count = db.Column(db.Integer, nullable=False, default=0)


class MerchantFraudCheck(db.Model):
    __tablename__ = "merchant_fraud_checks"

    id = db.Column(db.Integer, primary_key=True)
    merchant_id = db.Column(db.String(100), nullable=False, index=True)
    fraud_score = db.Column(db.Float, nullable=False)
    flags_json = db.Column(db.Text, nullable=False, default="[]")
    flagged_days_json = db.Column(db.Text, nullable=False, default="[]")
    checked_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)


class MerchantTierAssessment(db.Model):
    __tablename__ = "merchant_tier_assessments"

    id = db.Column(db.Integer, primary_key=True)
    merchant_id = db.Column(db.String(100), nullable=False, index=True)
    current_tier = db.Column(db.String(100), nullable=True)
    next_tier = db.Column(db.String(100), nullable=True)
    results_json = db.Column(db.Text, nullable=False, default="[]")
    assessed_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)


class PortfolioExposureSnapshot(db.Model):
    __tablename__ = "portfolio_exposure_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    tier_summary_json = db.Column(db.Text, nullable=False, default="[]")
    blocking_signals_json = db.Column(db.Text, nullable=False, default="[]")
    total_merchants = db.Column(db.Integer, nullable=False)
    total_estimated_exposure = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)


class MerchantDocumentVerification(db.Model):
    """Manual declaration check; distinct from uploaded-document OCR
    records."""

    __tablename__ = "merchant_document_verifications"

    id = db.Column(db.Integer, primary_key=True)
    merchant_id = db.Column(
        db.String(100), nullable=False, unique=True, index=True
    )
    gst_reported_monthly_revenue = db.Column(db.Float, nullable=False)
    bank_statement_avg_balance = db.Column(db.Float, nullable=False)
    bank_statement_monthly_inflow = db.Column(db.Float, nullable=False)
    consistent = db.Column(db.Boolean, nullable=False)
    mismatches_json = db.Column(db.Text, nullable=False, default="[]")
    verified_at = db.Column(
        db.DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    def set_mismatches(self, mismatches: list) -> None:
        self.mismatches_json = json.dumps(mismatches)

    def to_dict(self) -> dict:
        return {
            "merchant_id": self.merchant_id,
            "gst_reported_monthly_revenue": self.gst_reported_monthly_revenue,
            "bank_statement_avg_balance": self.bank_statement_avg_balance,
            "bank_statement_monthly_inflow": (
                self.bank_statement_monthly_inflow
            ),
            "consistent": self.consistent,
            "mismatches": json.loads(self.mismatches_json),
            "verified_at": (
                self.verified_at.isoformat() if self.verified_at else None
            ),
        }
