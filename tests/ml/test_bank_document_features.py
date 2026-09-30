from pathlib import Path
import pytest
from ml.documents.bank import parse_statement, bank_features, balance_check, BANK_FEATURES
from ml.documents.extraction import extract


def test_pdf_parse_and_every_feature():
    payload = (Path(__file__).parents[1] / "fixtures/documents/bank_statement.pdf").read_bytes()
    text, _, tables = extract(payload, 'application/pdf')
    rows = parse_statement(text, tables)
    assert len(rows) == 5
    assert balance_check(rows)['status'] == 'PASS'
    f = bank_features(rows)
    assert set(f) == set(BANK_FEATURES)
    assert f['avg_monthly_credits'] == 45000
    assert f['salary_regularity'] == 2
    assert f['avg_monthly_balance'] == pytest.approx(((4*10000+5*55000+22*50000)/31 + (4*50000+5*95000+85000)/10)/2)
    assert f['min_monthly_balance'] == 10000
    assert f['emi_debit_count'] == 1
    assert f['emi_debit_share'] == 0.5
    assert f['fixed_obligation_to_income_ratio'] == pytest.approx(5000/90000, abs=1e-6)
    assert f['bounced_payment_count'] == 0
    assert f['cash_withdrawal_share'] == pytest.approx(2/3, abs=1e-6)
    assert f['negative_balance_days'] == 0
    assert f['transaction_velocity'] == pytest.approx(4/41, abs=1e-6)
    assert f['income_volatility'] == 0


def test_csv_gaps_negative_balances_and_zero_income():
    text = 'date,description,debit,credit,balance\n2026-01-01,NSF returned,20,0,-10\n2026-03-01,Salary,0,100,90\n'
    rows = parse_statement(text, csv_mode=True)
    f = bank_features(rows)
    assert f['avg_monthly_credits'] == pytest.approx(100/3, abs=1e-6)
    assert f['negative_balance_days'] == 59
    assert f['bounced_payment_count'] == 1
    assert f['income_volatility'] > 1
    assert bank_features(rows[:1])['fixed_obligation_to_income_ratio'] is None
    assert all(v is None for v in bank_features([]).values())
    with pytest.raises(ValueError):
        parse_statement(text.replace('20,0', 'NaN,0'), csv_mode=True)


def test_pdf_table_parser():
    table = [['Date', 'Description', 'Debit', 'Credit', 'Balance'], ['2026-01-01', 'Salary', '0', '100', '100']]
    assert parse_statement('', [table])[0]['credit'] == 100


def test_synthetic_bank_generation_does_not_use_target():
    import pandas as pd
    from ml.data.synthetic_individual_bank import augment
    a = augment(pd.DataFrame({'credit_risk': [0, 1, 0]}))
    b = augment(pd.DataFrame({'credit_risk': [1, 0, 1]}))
    pd.testing.assert_frame_equal(a[BANK_FEATURES], b[BANK_FEATURES])


def test_flag_extends_explainer_schema_and_keeps_history_immutable():
    import os
    import subprocess
    import sys
    script = "from preprocessing.feature_config import NUMERIC_FEATURES, IMMUTABLE_FEATURES; from documents.bank import BANK_FEATURES; from prediction.predictor import FEATURE_COLUMNS; from explainability.shap_explainer import FEATURE_COLUMNS as SHAP; from explainability.lime_explainer import FEATURE_COLUMNS as LIME; from counterfactual.dice_explainer import FEATURE_COLUMNS as DICE; assert set(BANK_FEATURES) <= set(NUMERIC_FEATURES) & set(IMMUTABLE_FEATURES) & set(FEATURE_COLUMNS) & set(SHAP) & set(LIME) & set(DICE)"
    env = {**os.environ, 'BANK_DOCUMENT_FEATURES': 'true'}
    result = subprocess.run([sys.executable, '-c', script], cwd=Path(__file__).parents[2] / 'ml', env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
