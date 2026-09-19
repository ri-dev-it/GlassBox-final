# Machine Learning Pipeline

## Dataset

UCI Statlog German Credit Data -- see `ml/data/README.md` for full
documentation (source, fields, class distribution, protected-attribute caveat).

## Pipeline

```
python data/download_dataset.py   # fetch + label the real dataset (needs internet)
python training/train.py          # train, compare, select, save
```

## Synthetic merchant model

The additive merchant-risk path is trained with `python training/train_transaction_model.py`.
Its transaction features and labels are synthetic, simulated demo data only; they are not
real Razorpay merchant data and must not be treated as confirmed underwriting policy.

## Merchant fraud-pattern checks

`POST /api/merchants/fraud-check` runs the defensive, explainable rules in
`ml/fraud/pattern_detector.py` against daily transaction history. It checks
refund spikes, seven-day chargeback clusters, order-velocity anomalies, and
sharp GMV increases followed by elevated refunds. The score is a bounded
review signal, not proof of fraud and not a real-time Razorpay policy result.

## Illustrative Capital tiers and portfolio exposure

`ml/eligibility/gap_calculator.py` ranks merchants against simulated
`Starter Advance`, `Growth Capital`, and `Scale Capital` criteria. The
thresholds, tier names, and fixed exposure amounts are illustrative demo
values only, not Razorpay Capital policy. Merchant tier gaps are available at
`GET /api/merchants/<merchant_id>/tier-gaps`; portfolio aggregation is at
`GET /api/portfolio/exposure` and uses the synthetic Prompt 1 merchant data.

`train.py` trains Logistic Regression (baseline) and XGBoost (falls back
to RandomForest if xgboost isn't installed), evaluates both on the same
held-out test set (accuracy, precision, recall, F1, ROC-AUC, confusion
matrix), and selects the winner by F1 (not accuracy alone -- the dataset
is class-imbalanced ~70/30). Nothing is hardcoded; see `ml/training/train.py`.

## Three-band decisioning

Both predictors pass probability of default to `ml/decisioning/bands.py`.
By default, default probability below `0.15` returns `APPROVE`, values from
`0.15` up to but excluding `0.55` return `REVIEW`, and values at or above
`0.55` return `DECLINE`. Override these defaults with `APPROVE_BELOW` and
`DECLINE_AT_OR_ABOVE` environment variables. `REVIEW` means flagged for manual
underwriting review; these thresholds are configurable policy settings, not
probability recalibration.

Artifacts saved to `ml/models/saved/`:
- `model.joblib` -- the full sklearn Pipeline (preprocessing + classifier).
- `metadata.json` -- which model won, both models' metrics, dataset sizes.

Both `metadata.json` and `transaction_model_metadata.json` include precision,
recall, F1, and ROC-AUC computed on held-out test data. The admin metrics
comparison is served by `GET /api/analytics/models`; each current metadata
version is also snapshotted in the backend `model_metrics` table so history
is not limited to the latest JSON overwrite.

Before either model is saved or served, the Fairlearn governance gate checks
the configured disparity limits. A failed check is recorded in
`governance_checks`, prevents the training run from replacing the served
artifact, and causes the corresponding predictor to refuse inference.

## Grounded plain-English explanations

`ml/explain/grounded_explanation.py` optionally summarizes the top SHAP
drivers through an LLM. Its prompt contains only feature names and signed
contributions, never PII. The response must mention both top drivers or it is
discarded and replaced by a deterministic template. Missing API keys and LLM
errors also fall back cleanly. Results are cached in `grounded_explanations`
and served by the application and merchant explanation endpoints, with the UI
labeling the source as `AI-generated` or `System-generated`.

`ml/data/processed/test_with_predictions.csv` -- the held-out test set
with predictions attached, used by the fairness dashboard so it never
has to retrain or leak into training data.

## Partial dependence and counterfactual constraints

`GET /api/explain/partial-dependence` returns average predicted approval
probability curves for the numeric features, computed with
`sklearn.inspection.partial_dependence` on the saved pipeline and reference
data. These curves describe model behavior, not causal effects.

DiCE alternatives are filtered by a small dependency layer before they are
returned. It preserves loan amount/duration compatibility, employment/job
compatibility, housing/property compatibility, and high installment burden.
The response note identifies these checks; passing them does not
make a scenario a real-world lending recommendation.

## Why F1, not accuracy, decides the winner

With ~70% of applicants labeled "good credit," a model that always
predicts "approve" would score 70% accuracy while being useless. F1
balances precision and recall, which matters more for a system anyone
could actually deploy.
