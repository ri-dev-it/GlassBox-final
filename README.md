# GlassBox

[![CI](https://github.com/ri-dev-it/GlassBox/actions/workflows/ci.yml/badge.svg)](https://github.com/ri-dev-it/GlassBox/actions/workflows/ci.yml)

**An explainable, self-auditing AI Risk Manager for Razorpay Capital.**

GlassBox scores merchant and applicant risk, explains every decision in
plain language, tells rejected or borderline applicants exactly what
would change the outcome, audits itself for fairness before it's allowed
to serve predictions, detects fraud patterns in real time, and shows
which capital tier a merchant qualifies for — including how far away
they are from the next one.

> Built for the **Razorpay AI Buildathon 2026 — AI Risk Manager track**.

---

## Why this exists

Razorpay Capital underwrites merchants using their own transaction
data — GMV, refund rate, chargeback rate, payment success rate — not
just static bureau data. But that kind of behavioral underwriting is
usually a black box: a merchant gets a yes/no with no way to see why, no
path to improve, and no visibility into whether the system is treating
similar merchants fairly.

**GlassBox is built around one idea: every decision should be
explainable, actionable, and auditable — and the system should manage
the risk of its own model being wrong, unfair, or misunderstood, not
just the applicant's risk.**

---

## What it does

### Core risk assessment
- **Predicts** risk two ways: a traditional income/credit-score model
  (Logistic Regression vs. XGBoost, selected on held-out F1/ROC-AUC) and
  a **transaction-behavior model** using GMV trend, payment success
  rate, refund rate, chargeback rate, customer concentration, and order
  volume volatility — the kind of signal Razorpay Capital actually has
  access to that a traditional bank doesn't
- **Decides in three bands, not a binary cutoff** — APPROVE / REVIEW /
  DECLINE, calibrated against configurable risk thresholds instead of a
  flat probability cutoff, so borderline cases route to human review
  instead of a hard yes/no
- **Explains** every decision with SHAP (local + global) and LIME, with
  an explicit view of where the two methods agree or disagree

### Trust and recourse
- **Shows recourse** — DiCE-generated counterfactuals ("what would need
  to change") that respect immutable and protected features
- **Grounded AI explanations** — an LLM turns raw SHAP output into a
  plain-English explanation, but only after a validation check confirms
  the explanation actually references the model's real top drivers; if
  it can't be verified, the system falls back to a deterministic
  template instead of ever showing an ungrounded explanation
- **Audits itself for fairness** — a Fairlearn-based audit across
  protected groups (selection rate, TPR/FPR, demographic parity,
  equalized odds), with an explicit disparity threshold and a documented
  proxy-attribute caveat
- **Governance gate** — a model version that fails its own fairness or
  calibration thresholds is not allowed to serve predictions; the system
  keeps the last known-good governed model in place and flags the
  failure clearly instead of silently deploying a worse one

### Risk detection and portfolio view
- **Fraud pattern detection** — a transparent, rules-based detector that
  flags refund spikes, chargeback clusters, order-velocity anomalies,
  and GMV-refund mismatches in a merchant's transaction history, each
  flag human-readable and auditable, not a black-box fraud score
- **Simulated document verification** — checks manually-entered
  document values (e.g., GST-reported revenue) against actual
  transaction data, flagging inconsistencies as an additional risk
  signal (explicitly simulated, not real OCR/document parsing — see
  caveats below)
- **Tier-based gap calculator** — for merchants not yet qualifying for a
  higher Razorpay Capital tier, shows exactly how much their GMV trend,
  refund rate, or customer concentration would need to improve, ranked
  by how close they already are
- **Portfolio exposure dashboard** — an aggregate view across all
  merchants: how many sit in each tier, total estimated capital
  exposure per tier, and which risk signal most commonly blocks tier
  advancement across the whole portfolio

### Visibility
- **Precision, recall, F1, and ROC-AUC** surfaced clearly on the admin
  dashboard for both models, side by side — not buried in a notebook

---

## Important notes (read before trusting any number here)

- SHAP/LIME explain model *behavior*; they do not prove causation.
- Counterfactuals describe what would change the *model's* prediction,
  not a guarantee of real-world approval.
- Fairness metrics are reported with an explicit disparity threshold and
  a documented proxy-attribute caveat — never as a blanket "the model is
  fair."
- The transaction-behavior dataset is **synthetic**, generated to
  reflect realistic relationships between merchant signals and risk —
  it is not real Razorpay merchant data.
- Razorpay Capital tier thresholds and portfolio exposure figures are
  **illustrative/simulated for demo purposes**, not real Razorpay
  Capital policy.
- Document verification is a **simulated** feature — merchants manually
  enter values as if extracted from documents; there is no real
  OCR/file-parsing pipeline.
- Grounded AI explanations are clearly labeled "AI-generated" vs.
  "system-generated" depending on whether the LLM's output passed the
  grounding check — the system never presents an unverified explanation
  as if it were verified.
- No fabricated data, predictions, explanations, or fairness metrics
  anywhere — every number comes from real computation on real, cited, or
  clearly-labeled-synthetic data.

---

## Architecture

```
project-root/
├── frontend/    React + TypeScript + Vite + Tailwind CSS
├── backend/     Python + Flask REST API (routes -> services -> ML/DB)
├── ml/          Models, training, explainability, fairness, decisioning,
│                fraud detection, eligibility/gap logic, document
│                verification, grounded explanation layer
├── database/    MySQL schema + migrations + seed scripts
├── tests/       Backend (pytest), ML (pytest), frontend (Vitest)
└── docs/        Architecture, API, database, ML, explainability,
                 fairness, fraud detection, portfolio, testing
```

See `docs/` for the deep-dive on each area.

## Technology stack

| Layer    | Stack                                                                     |
| -------- | ------------------------------------------------------------------------- |
| Frontend | React, TypeScript, Vite, Tailwind CSS, React Router, Axios, Recharts      |
| Backend  | Python, Flask, Flask-CORS, Flask-SQLAlchemy, Flask-Bcrypt, PyJWT          |
| ML       | Pandas, NumPy, scikit-learn, XGBoost, SHAP, LIME, DiCE, Fairlearn, Joblib |
| AI       | Anthropic API (grounded explanation layer, with deterministic fallback)  |
| Database | MySQL                                                                     |

---

## Installation

### Prerequisites
Node.js 18+, Python 3.11+, MySQL 8+, and an internet connection (to
download the dataset and install packages). An Anthropic API key is
optional — the grounded explanation layer falls back to a deterministic
template automatically if one isn't configured.

### 1. Environment
```bash
cp .env.example backend/.env
# edit backend/.env: DB credentials, a real SECRET_KEY, and (optionally)
# an Anthropic API key for the grounded explanation layer
```

### 2. Database
```sql
CREATE DATABASE glassbox_db CHARACTER SET utf8mb4;
```
Set `MYSQL_*` / `DATABASE_URL` in `backend/.env` to match, then apply
migrations (see `database/`).

### 3. Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
flask db upgrade
python run.py
```
API on **http://localhost:5000**. Verify: `curl http://localhost:5000/api/health`.

### 4. Train the models (required before predictions work)
```bash
cd ml
python data/download_dataset.py            # real UCI dataset -- needs internet
python data/synthetic_transactions.py       # generates synthetic merchant data
python training/train.py                    # income/credit-score model
python training/train_transaction_model.py  # transaction-behavior model
```
This writes both models plus their metadata (including governance and
fairness results) to `ml/models/saved/`, which the backend depends on —
you'll get a clear error if you skip this step.

### 5. First admin account
```bash
cd backend
python ../database/seeds/seed_admin.py admin@example.com "Admin Name" a-strong-password
```

### 6. Frontend
```bash
cd frontend
npm install
npm run dev
```
App on **http://localhost:5173**.

### 7. Testing
```bash
cd backend && pytest ../tests/backend -v
cd ml && pytest ../tests/ml -v
cd frontend && npm run test
```

---

## Why "AI Risk Manager"

Razorpay's own framing for this track asks for a working detector,
verifier, or auto-responder for one class of loss, evaluated on measured
precision and recall. GlassBox is a working risk detector for both
traditional and transaction-behavior-based underwriting — extended with
the parts that make a risk model trustworthy enough to actually deploy:

- **Detection** — two working risk models plus a dedicated fraud
  pattern detector, all reporting real precision/recall/AUC
- **Policy** — three-band decisioning instead of a hard cutoff
- **Explanation** — SHAP/LIME/DiCE plus a grounded, hallucination-checked
  plain-English layer
- **Self-audit** — a fairness audit with a governance gate that blocks
  its own bad models
- **Recourse** — counterfactuals and a tier-gap calculator that show a
  real path forward, not just a rejection

That's the actual difference between a model that predicts risk and a
system that *manages* it.

---

## About

Built solo for the Razorpay AI Buildathon 2026, AI Risk Manager track.
