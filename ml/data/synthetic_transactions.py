"""Synthetic merchant transactions for demo and development purposes only.

This module does not contain real Razorpay merchant data. It generates
simulated transaction behavior with intentionally learnable relationships
between operating signals and a synthetic default/risk label.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TRANSACTION_FEATURES = [
    "gmv_trend_30d",
    "gmv_trend_90d",
    "payment_success_rate",
    "refund_rate",
    "chargeback_rate",
    "customer_concentration",
    "order_volume_volatility",
    "account_age_days",
]

TRANSACTION_LABELS = {
    "gmv_trend_30d": "GMV trend (30 days)",
    "gmv_trend_90d": "GMV trend (90 days)",
    "payment_success_rate": "Payment success rate",
    "refund_rate": "Refund rate",
    "chargeback_rate": "Chargeback rate",
    "customer_concentration": "Customer concentration",
    "order_volume_volatility": "Order volume volatility",
    "account_age_days": "Account age",
}

TRANSACTION_RANGES = {
    "gmv_trend_30d": (-1.0, 2.0),
    "gmv_trend_90d": (-1.0, 2.0),
    "payment_success_rate": (0.0, 1.0),
    "refund_rate": (0.0, 1.0),
    "chargeback_rate": (0.0, 1.0),
    "customer_concentration": (0.0, 1.0),
    "order_volume_volatility": (0.0, 3.0),
    "account_age_days": (1.0, 10000.0),
}


def generate_synthetic_transactions(
    n_merchants: int = 2500, random_state: int = 42
) -> pd.DataFrame:
    """Return simulated merchant transaction features and a synthetic label.

    The ``defaulted`` column is a synthetic outcome for model demonstrations,
    not a representation of Razorpay underwriting or real merchant behavior.
    Higher refunds, chargebacks, concentration, volatility, and declining GMV
    increase the generated risk probability.
    """
    if n_merchants < 20:
        raise ValueError(
            "n_merchants must be at least 20 for a useful dataset"
        )

    rng = np.random.default_rng(random_state)
    account_age_days = rng.integers(30, 3651, n_merchants)
    merchant_quality = rng.normal(0, 1, n_merchants)

    gmv_trend_90d = np.clip(
        0.18 * merchant_quality + rng.normal(0, 0.18, n_merchants), -0.65, 0.75
    )
    gmv_trend_30d = np.clip(
        gmv_trend_90d + rng.normal(0, 0.12, n_merchants), -0.75, 0.85
    )
    payment_success_rate = np.clip(
        0.94 + 0.025 * merchant_quality + rng.normal(0, 0.018, n_merchants),
        0.72,
        0.999,
    )
    refund_rate = np.clip(
        0.055 - 0.018 * merchant_quality + rng.normal(0, 0.018, n_merchants),
        0.002,
        0.30,
    )
    chargeback_rate = np.clip(
        0.012 - 0.005 * merchant_quality + rng.normal(0, 0.006, n_merchants),
        0.0005,
        0.12,
    )
    customer_concentration = np.clip(
        0.20 - 0.045 * merchant_quality + rng.normal(0, 0.07, n_merchants),
        0.03,
        0.95,
    )
    order_volume_volatility = np.clip(
        0.45 - 0.10 * merchant_quality + rng.normal(0, 0.12, n_merchants),
        0.05,
        1.8,
    )

    risk_signal = (
        1.25 * (-gmv_trend_30d)
        + 0.80 * (-gmv_trend_90d)
        + 4.0 * (0.96 - payment_success_rate)
        + 5.0 * refund_rate
        + 8.0 * chargeback_rate
        + 1.25 * customer_concentration
        + 0.75 * order_volume_volatility
        - 0.00008 * account_age_days
        + rng.normal(0, 0.18, n_merchants)
    )
    default_probability = 1 / (1 + np.exp(-(risk_signal - 0.75)))
    defaulted = rng.binomial(1, default_probability)

    return pd.DataFrame(
        {
            "gmv_trend_30d": gmv_trend_30d,
            "gmv_trend_90d": gmv_trend_90d,
            "payment_success_rate": payment_success_rate,
            "refund_rate": refund_rate,
            "chargeback_rate": chargeback_rate,
            "customer_concentration": customer_concentration,
            "order_volume_volatility": order_volume_volatility,
            "account_age_days": account_age_days,
            "defaulted": defaulted,
        }
    )


if __name__ == "__main__":
    print(generate_synthetic_transactions().head())
