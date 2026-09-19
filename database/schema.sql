-- MySQL schema for the Explainable AI Loan Approval System (Milestone 3).
-- Flask-Migrate manages this in normal operation (see backend/README
-- section on `flask db upgrade`); this file is the reproducible reference
-- schema / can be run directly for a fresh setup.

CREATE DATABASE IF NOT EXISTS xai_loan_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE xai_loan_db;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'applicant',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_users_email (email)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS applicants (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_applicants_user (user_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS applications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    public_id VARCHAR(20) UNIQUE,
    applicant_id INT NOT NULL,
    features_json TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    admin_decision VARCHAR(20) NULL,
    admin_decided_by INT NULL,
    admin_decided_at DATETIME NULL,
    FOREIGN KEY (applicant_id) REFERENCES applicants(id) ON DELETE CASCADE,
    FOREIGN KEY (admin_decided_by) REFERENCES users(id),
    INDEX idx_applications_applicant (applicant_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS predictions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    application_id INT NOT NULL UNIQUE,
    decision VARCHAR(20) NOT NULL,
    probability FLOAT NOT NULL,
    model_name VARCHAR(50) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS explanations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    prediction_id INT NOT NULL,
    method VARCHAR(10) NOT NULL,
    contributions_json TEXT NOT NULL,
    plain_english TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prediction_id) REFERENCES predictions(id) ON DELETE CASCADE,
    UNIQUE KEY uq_prediction_method (prediction_id, method),
    INDEX idx_explanations_prediction (prediction_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS grounded_explanations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    application_id INT NULL UNIQUE,
    merchant_id VARCHAR(100) NULL UNIQUE,
    text TEXT NOT NULL,
    source VARCHAR(20) NOT NULL,
    grounded_in_json TEXT NOT NULL,
    generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE,
    INDEX idx_grounded_explanations_application (application_id),
    INDEX idx_grounded_explanations_merchant (merchant_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS counterfactuals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    prediction_id INT NOT NULL,
    found BOOLEAN NOT NULL DEFAULT FALSE,
    message TEXT,
    alternatives_json TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prediction_id) REFERENCES predictions(id) ON DELETE CASCADE,
    INDEX idx_counterfactuals_prediction (prediction_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS documents (
    id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL, application_id INT NULL,
    document_type VARCHAR(40) NOT NULL, storage_reference VARCHAR(512) NOT NULL UNIQUE,
    original_filename VARCHAR(255) NOT NULL, mime_type VARCHAR(100) NOT NULL,
    file_size INT NOT NULL, status VARCHAR(20) NOT NULL, uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE,
    INDEX idx_documents_user (user_id), INDEX idx_documents_application (application_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS document_verifications (
    id INT AUTO_INCREMENT PRIMARY KEY, document_id INT NOT NULL UNIQUE, status VARCHAR(20) NOT NULL,
    confidence FLOAT NOT NULL, extracted_information_json TEXT NOT NULL, mismatches_json TEXT NOT NULL,
    verification_message VARCHAR(1000) NOT NULL, verified_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS bank_eligibility_results (
    id INT AUTO_INCREMENT PRIMARY KEY, application_id INT NOT NULL, bank_name VARCHAR(100) NOT NULL,
    decision VARCHAR(20) NOT NULL, probability FLOAT NOT NULL, reasons_json TEXT NOT NULL,
    conditions_json TEXT NOT NULL, risk_indicators_json TEXT NOT NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE,
    INDEX idx_bank_eligibility_application (application_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS merchant_transaction_profiles (
    id INT AUTO_INCREMENT PRIMARY KEY, merchant_id VARCHAR(100) NOT NULL UNIQUE,
    gmv_trend_30d FLOAT NOT NULL, gmv_trend_90d FLOAT NOT NULL, payment_success_rate FLOAT NOT NULL,
    refund_rate FLOAT NOT NULL, chargeback_rate FLOAT NOT NULL, customer_concentration FLOAT NOT NULL,
    order_volume_volatility FLOAT NOT NULL, account_age_days FLOAT NOT NULL,
    actual_monthly_gmv FLOAT NOT NULL, actual_monthly_inflow FLOAT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS merchant_transaction_history (
    id INT AUTO_INCREMENT PRIMARY KEY, merchant_id VARCHAR(100) NOT NULL, transaction_date DATE NOT NULL,
    gmv FLOAT NOT NULL, refund_count INT NOT NULL DEFAULT 0, chargeback_count INT NOT NULL DEFAULT 0,
    order_count INT NOT NULL DEFAULT 0, INDEX idx_transaction_history_merchant (merchant_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS merchant_fraud_checks (
    id INT AUTO_INCREMENT PRIMARY KEY, merchant_id VARCHAR(100) NOT NULL, fraud_score FLOAT NOT NULL,
    flags_json TEXT NOT NULL, flagged_days_json TEXT NOT NULL, checked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_fraud_checks_merchant (merchant_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS merchant_tier_assessments (
    id INT AUTO_INCREMENT PRIMARY KEY, merchant_id VARCHAR(100) NOT NULL, current_tier VARCHAR(100) NULL,
    next_tier VARCHAR(100) NULL, results_json TEXT NOT NULL, assessed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_tier_assessments_merchant (merchant_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS portfolio_exposure_snapshots (
    id INT AUTO_INCREMENT PRIMARY KEY, tier_summary_json TEXT NOT NULL, blocking_signals_json TEXT NOT NULL,
    total_merchants INT NOT NULL, total_estimated_exposure FLOAT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS merchant_document_verifications (
    id INT AUTO_INCREMENT PRIMARY KEY, merchant_id VARCHAR(100) NOT NULL UNIQUE,
    gst_reported_monthly_revenue FLOAT NOT NULL, bank_statement_avg_balance FLOAT NOT NULL,
    bank_statement_monthly_inflow FLOAT NOT NULL, consistent BOOLEAN NOT NULL,
    mismatches_json TEXT NOT NULL, verified_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_merchant_document_verifications_merchant (merchant_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS model_metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    model_key VARCHAR(100) NOT NULL,
    model_version VARCHAR(100) NOT NULL,
    precision FLOAT NOT NULL,
    recall FLOAT NOT NULL,
    f1 FLOAT NOT NULL,
    roc_auc FLOAT NOT NULL,
    dataset_size INT NULL,
    test_size INT NULL,
    evaluated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_model_metrics_model_key (model_key)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS governance_checks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    model_key VARCHAR(100) NOT NULL,
    model_version VARCHAR(100) NOT NULL,
    passed BOOLEAN NOT NULL,
    failed_checks_json TEXT NOT NULL,
    checked_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_governance_checks_model_key (model_key)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS model_versions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    model_name VARCHAR(50) NOT NULL,
    version_number INT NOT NULL,
    trained_at DATETIME NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    metrics_json TEXT NOT NULL,
    governance_passed BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE KEY uq_model_versions_name_number (model_name, version_number),
    INDEX idx_model_versions_name (model_name),
    INDEX idx_model_versions_active (is_active)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS ab_tests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    model_name VARCHAR(50) NOT NULL,
    name VARCHAR(120) NOT NULL,
    control_version_id INT NOT NULL,
    treatment_version_id INT NOT NULL,
    traffic_percentage FLOAT NOT NULL DEFAULT 50,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at DATETIME NULL,
    FOREIGN KEY (control_version_id) REFERENCES model_versions(id),
    FOREIGN KEY (treatment_version_id) REFERENCES model_versions(id),
    INDEX idx_ab_tests_model_status (model_name, status)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS ab_test_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ab_test_id INT NOT NULL,
    prediction_id INT NULL,
    variant VARCHAR(20) NOT NULL,
    model_version_id INT NOT NULL,
    decision VARCHAR(20) NOT NULL,
    probability FLOAT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ab_test_id) REFERENCES ab_tests(id) ON DELETE CASCADE,
    FOREIGN KEY (prediction_id) REFERENCES predictions(id) ON DELETE SET NULL,
    FOREIGN KEY (model_version_id) REFERENCES model_versions(id),
    INDEX idx_ab_test_results_test (ab_test_id),
    INDEX idx_ab_test_results_prediction (prediction_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS grounded_explanations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    application_id INT NULL UNIQUE,
    merchant_id VARCHAR(100) NULL UNIQUE,
    text TEXT NOT NULL,
    source VARCHAR(20) NOT NULL,
    grounded_in_json TEXT NOT NULL,
    generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE,
    INDEX idx_grounded_explanations_application (application_id),
    INDEX idx_grounded_explanations_merchant (merchant_id)
) ENGINE=InnoDB;
