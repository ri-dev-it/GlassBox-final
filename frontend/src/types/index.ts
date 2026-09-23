export type Role = 'applicant' | 'client' | 'loan_officer' | 'admin';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  created_at: string;
}

export interface AdminOverview {
  pending_review: number;
  approved_today: number;
  rejected_today: number;
  active_models: number;
  governed_models: number;
  governance_passed: boolean;
}

export interface AuthResponse {
  token: string;
  user: User;
}

export type ApplicantFeatures = Record<string, string | number>;

export interface PredictionResult {
  id: number;
  application_id: number;
  decision: 'APPROVE' | 'REVIEW' | 'DECLINE' | 'APPROVED' | 'REJECTED';
  probability: number;
  risk_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  model_name: string;
  created_at: string;
}

export interface Contribution {
  feature: string;
  label: string;
  value: string | number;
  contribution: number;
  direction: 'positive' | 'negative';
}

export interface ExplanationResult {
  id?: number;
  prediction_id?: number;
  method?: 'shap' | 'lime';
  contributions: Contribution[];
  plain_english: string;
}

export interface PartialDependencePoint {
  value: number;
  approval_probability: number;
}

export interface PartialDependenceCurve {
  feature: string;
  label: string;
  points: PartialDependencePoint[];
}

export interface GroundedExplanation {
  id: number;
  application_id: number | null;
  merchant_id: string | null;
  text: string;
  source: 'llm' | 'template';
  grounded_in: string[];
  generated_at: string | null;
}

export interface MerchantTransactionFeatures {
  gmv_trend_30d: number;
  gmv_trend_90d: number;
  payment_success_rate: number;
  refund_rate: number;
  chargeback_rate: number;
  customer_concentration: number;
  order_volume_volatility: number;
  account_age_days: number;
}

export interface MerchantAssessment {
  prediction: {
    prediction: 'APPROVE' | 'REVIEW' | 'DECLINE';
    probability: number;
    risk_score: number;
    risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
    model_name: string;
  };
  shap: ExplanationResult;
  fraud: FraudCheckResult | null;
  document_verification: DocumentConsistencyResult | null;
  risk_signals: string[];
  disclaimer: string;
}

export interface DocumentMismatch {
  field: string;
  declared_value: number;
  expected_value: number;
  discrepancy_pct: number;
  message: string;
}

export interface DocumentConsistencyResult {
  merchant_id: string;
  gst_reported_monthly_revenue: number;
  bank_statement_avg_balance: number;
  bank_statement_monthly_inflow: number;
  consistent: boolean;
  mismatches: DocumentMismatch[];
  verified_at: string | null;
}

export interface MerchantTransactionDay {
  date: string;
  gmv: number;
  refund_count: number;
  chargeback_count: number;
  order_count: number;
}

export interface FraudCheckResult {
  merchant_id: string;
  fraud_score: number;
  flags: string[];
  flagged_days: string[];
}

export interface TierGap {
  feature: string;
  current_value: number;
  required_value: number;
  delta: number;
  direction: 'increase' | 'decrease';
  human_message: string;
}

export interface TierEligibilityResult {
  tier: string;
  eligible: boolean;
  gaps: TierGap[];
  overall_message: string;
}

export interface MerchantTierGaps {
  merchant_id: string;
  current_tier: string | null;
  next_tier: string | null;
  next_tier_gap: TierEligibilityResult | null;
  tiers: TierEligibilityResult[];
  disclaimer: string;
}

export interface PortfolioExposure {
  tier_summary: Array<{ tier: string; merchant_count: number; estimated_exposure: number }>;
  blocking_signals: Array<{ feature: string; merchant_count: number }>;
  total_merchants: number;
  total_estimated_exposure: number;
  disclaimer: string;
}

export interface ComparisonResult {
  agreement: Array<{
    feature: string;
    label: string;
    shap_contribution: number;
    lime_contribution: number;
    shap_direction: string;
    lime_direction: string;
  }>;
  direction_disagreement: Array<{
    feature: string;
    label: string;
    shap_contribution: number;
    lime_contribution: number;
    shap_direction: string;
    lime_direction: string;
  }>;
  shap_only_top_features: string[];
  lime_only_top_features: string[];
  note: string;
}

export interface CounterfactualAlternative {
  [feature: string]: { label: string; current: string | number; suggested: string | number };
}

export interface CounterfactualResult {
  found: boolean;
  message: string;
  current_profile: ApplicantFeatures;
  alternatives: CounterfactualAlternative[];
}

export interface ApplicationDetail {
  application: {
    id: number;
    application_id: string;
    status: string;
    admin_decision?: string | null;
    applicant_id: number;
    features: ApplicantFeatures;
    created_at: string;
    loan_type?: LoanType;
  };
  prediction: PredictionResult | null;
  shap: ExplanationResult | null;
  lime: ExplanationResult | null;
  comparison: ComparisonResult | null;
  counterfactual: CounterfactualResult | null;
  documents?: DocumentRecord[];
  bankEligibility?: BankEligibilityResult[];
}

export interface AnalysisReportFactor {
  feature: string;
  label: string;
  value: string | number;
  contribution: number;
  direction: 'positive' | 'negative';
  reason: string;
}

export interface AnalysisReport {
  application_id: string;
  decision: 'APPROVE' | 'REVIEW' | 'DECLINE' | 'APPROVED' | 'REJECTED';
  probability: number;
  confidence: number;
  factors: AnalysisReportFactor[];
  lime: { summary: string; factors: AnalysisReportFactor[] };
  risk: { score: number; level: 'LOW' | 'MEDIUM' | 'HIGH' };
  disclaimer: string;
}

export type LoanType = 'PERSONAL_LOAN' | 'CAR_LOAN' | 'BIKE_LOAN' | 'HOME_LOAN' | 'BUSINESS_CAPITAL' | 'EDUCATION_LOAN';
export type DocumentStatus = 'UPLOADED' | 'VERIFYING' | 'VERIFIED' | 'NEEDS_REVIEW' | 'FAILED';
export type DocumentType = 'PAN_CARD' | 'AADHAAR_CARD' | 'SALARY_SLIP' | 'BANK_STATEMENT' | 'ADDRESS_PROOF' | 'EMPLOYMENT_INCOME_PROOF';
export interface DocumentVerification { documentType: DocumentType; status: DocumentStatus; confidence: number; extractedInformation: Record<string, unknown>; mismatches: string[]; verificationMessage: string; verifiedAt?: string; }
export interface DocumentRecord { id: number; documentType: DocumentType; status: DocumentStatus; filename: string; uploadedAt?: string; verification?: DocumentVerification | null; documentStatus?: 'pending' | 'approved' | 'rejected'; reviewedBy?: number | null; reviewedAt?: string | null; }
export interface BankEligibilityResult { bankName: string; decision: 'APPROVED' | 'NOT_ELIGIBLE' | 'NEEDS_REVIEW'; probability: number; reasons: string[]; conditions: string[]; riskIndicators: string[]; }

export interface ModelMetadata {
  final_model: string;
  precision: number;
  recall: number;
  f1: number;
  roc_auc: number;
  trained_at: string;
  dataset_size: number;
  train_size: number;
  test_size: number;
  feature_columns: string[];
  target_column: string;
  protected_attribute: string;
  model_comparison: Record<string, {
    accuracy: number; precision: number; recall: number; f1: number; roc_auc?: number;
    confusion_matrix: number[][];
  }>;
}

export interface GlobalShapEntry {
  feature: string;
  label: string;
  mean_abs_shap: number;
}

export interface ModelMetricSnapshot {
  model_key: string;
  model_version: string;
  precision: number;
  recall: number;
  f1: number;
  roc_auc: number;
  dataset_size: number | null;
  test_size: number | null;
  evaluated_at: string | null;
  governance: GovernanceStatus;
}

export interface GovernanceStatus {
  model_key: string;
  model_version: string;
  passed: boolean;
  failed_checks: string[];
  checked_at: string | null;
}

export interface ModelsMetrics {
  latest: Record<string, ModelMetricSnapshot>;
  history: Record<string, ModelMetricSnapshot[]>;
}

export interface ABTest {
  id: number;
  model_name: string;
  name: string;
  control_version_id: number;
  treatment_version_id: number;
  traffic_percentage: number;
  status: 'active' | 'ended';
  started_at: string | null;
  ended_at: string | null;
}

export interface ABTestSummary {
  count: number;
  approved: number;
  approval_rate: number | null;
  average_probability: number | null;
}

export interface ABTestResults {
  test: ABTest;
  summary: { control: ABTestSummary; treatment: ABTestSummary };
  results: Array<{ id: number; variant: 'control' | 'treatment'; model_version_id: number; decision: string; probability: number; created_at: string | null }>;
}

export interface ModelVersion {
  id: number;
  model_name: string;
  version_number: number;
  trained_at: string | null;
  file_path: string;
  metrics: Record<string, number>;
  governance_passed: boolean;
  is_active: boolean;
}

export interface FairnessReport {
  protected_attribute: string;
  protected_attribute_caveat: string;
  group_metrics: Record<string, Record<string, number>>;
  overall_metrics: { accuracy: number; selection_rate: number };
  disparity_metrics: { demographic_parity_difference: number; equalized_odds_difference: number };
  interpretation: string[];
  sample_size: number;
  disclaimer: string;
}

export interface ApplicationsSummary {
  total: number;
  approved: number;
  rejected: number;
  review?: number;
  approval_rate: number | null;
}
