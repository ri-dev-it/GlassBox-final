import axios from 'axios';
import type {
  AuthResponse, ApplicantFeatures, ApplicationDetail, ExplanationResult, GroundedExplanation, PartialDependenceCurve,
  CounterfactualResult, ModelMetadata, GlobalShapEntry, FairnessReport,
  ApplicationsSummary, AdminOverview,
  AnalysisReport,
  DocumentConsistencyResult, DocumentRecord, DocumentType, FraudCheckResult, MerchantAssessment, MerchantTierGaps, MerchantTransactionDay, MerchantTransactionFeatures, ModelsMetrics, PortfolioExposure, ABTest, ABTestResults, ModelVersion,
} from '../types';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Attach the JWT (if present) to every outgoing request.
api.interceptors.request.use((config) => {
  // FormData must retain the browser-generated multipart boundary. The JSON
  // default configured above is appropriate for API payloads, not uploads.
  if (typeof FormData !== 'undefined' && config.data instanceof FormData) {
    config.headers?.delete?.('Content-Type');
    if (config.headers && !config.headers.delete) delete (config.headers as Record<string, unknown>)['Content-Type'];
  }
  const token = localStorage.getItem('xai_loan_token');
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export interface HealthCheckResponse {
  status: string;
  service: string;
  version: string;
}

export const healthApi = {
  check: () => api.get<HealthCheckResponse>('/health').then((r) => r.data),
};

export const authApi = {
  register: (payload: { email: string; password: string; full_name: string; role: 'client' | 'admin' }) =>
    api.post<AuthResponse>('/auth/register', payload).then((r) => r.data),
  login: (payload: { email: string; password: string }) =>
    api.post<AuthResponse>('/auth/login', payload).then((r) => r.data),
  logout: () => api.post('/auth/logout').then((r) => r.data),
  me: () => api.get<{ user: AuthResponse['user'] }>('/auth/me').then((r) => r.data.user),
};

export const applicationApi = {
  submit: (features: ApplicantFeatures) =>
    api.post<ApplicationDetail>('/predict', features).then((r) => r.data),
  list: () => api.get<{ applications: ApplicationDetail['application'][] }>('/applications').then((r) => r.data.applications),
  getById: (id: number) => api.get<ApplicationDetail>(`/applications/${id}`).then((r) => r.data),
  report: (id: number) => api.get<{ report: AnalysisReport }>(`/applications/${id}/report`).then((r) => r.data.report),
  downloadReport: (id: number) => api.get(`/applications/${id}/report.pdf`, { responseType: 'blob' }).then((r) => r.data as Blob),
};

export interface AdminReviewApplication {
  id: number;
  application_id: string;
  status: string;
  applicant_id: number;
  features: ApplicantFeatures;
  created_at: string;
  admin_decision: string | null;
  admin_decided_by: number | null;
  admin_decided_at: string | null;
  prediction: import('../types').PredictionResult;
  applicant: { full_name: string; email: string };
  shap: ExplanationResult | null;
  lime: ExplanationResult | null;
  counterfactual: CounterfactualResult | null;
}

export const adminApi = {
  overview: () => api.get<AdminOverview>('/admin/overview').then((r) => r.data),
  pendingReviews: () => api.get<{ applications: AdminReviewApplication[] }>('/admin/applications/review').then((r) => r.data.applications),
  decideReview: (applicationId: number, decision: 'APPROVE' | 'REJECT') => api.post<{ application: AdminReviewApplication }>(`/admin/applications/${applicationId}/review`, { decision }).then((r) => r.data.application),
};

export const documentApi = {
  pending: () => api.get<{ documents: DocumentRecord[] }>('/documents/pending').then((r) => r.data.documents),
  upload: (documentType: DocumentType, file: File) => {
    const body = new FormData(); body.append('documentType', documentType); body.append('file', file);
    return api.post<{ document: DocumentRecord }>('/documents', body).then((r) => r.data.document);
  },
};

export const explanationApi = {
  groundedApplication: (applicationId: number) => api.get<GroundedExplanation>(`/explain/${applicationId}`).then((r) => r.data),
  groundedMerchant: (merchantId: string) => api.get<GroundedExplanation>(`/explain/merchant/${encodeURIComponent(merchantId)}`).then((r) => r.data),
  shap: (features: ApplicantFeatures) =>
    api.post<{ prediction: unknown } & ExplanationResult>('/explain/shap', features).then((r) => r.data),
  lime: (features: ApplicantFeatures) =>
    api.post<{ prediction: unknown } & ExplanationResult>('/explain/lime', features).then((r) => r.data),
  counterfactual: (features: ApplicantFeatures) =>
    api.post<CounterfactualResult>('/explain/counterfactual', features).then((r) => r.data),
  partialDependence: () => api.get<{ curves: PartialDependenceCurve[] }>('/explain/partial-dependence').then((r) => r.data.curves),
};

export const merchantApi = {
  assess: (features: MerchantTransactionFeatures & { merchant_id: string; transaction_history: MerchantTransactionDay[] }) =>
    api.post<MerchantAssessment>('/merchants/assess', features).then((r) => r.data),
  fraudCheck: (merchant_id: string, transaction_history: MerchantTransactionDay[]) =>
    api.post<FraudCheckResult>('/merchants/fraud-check', { merchant_id, transaction_history }).then((r) => r.data),
  tierGaps: (merchantId: string, features?: MerchantTransactionFeatures) => api.get<MerchantTierGaps>(`/merchants/${encodeURIComponent(merchantId)}/tier-gaps`, { params: features }).then((r) => r.data),
  verifyDocuments: (merchantId: string, declared: { gst_reported_monthly_revenue: number; bank_statement_avg_balance: number; bank_statement_monthly_inflow: number }) => api.post<DocumentConsistencyResult>(`/merchants/${encodeURIComponent(merchantId)}/verify-documents`, declared).then((r) => r.data),
  getDocumentVerification: (merchantId: string) => api.get<DocumentConsistencyResult | { merchant_id: string; verification: null }>(`/merchants/${encodeURIComponent(merchantId)}/verify-documents`).then((r) => r.data),
};

export const portfolioApi = {
  exposure: () => api.get<PortfolioExposure>('/portfolio/exposure').then((r) => r.data),
};

export const analyticsApi = {
  model: () => api.get<ModelMetadata>('/analytics/model').then((r) => r.data),
  models: () => api.get<ModelsMetrics>('/analytics/models').then((r) => r.data),
  globalShap: () => api.get<{ global_importance: GlobalShapEntry[] }>('/analytics/shap').then((r) => r.data.global_importance),
  fairness: () => api.get<FairnessReport>('/analytics/fairness').then((r) => r.data),
  applicationsSummary: () => api.get<ApplicationsSummary>('/analytics/applications-summary').then((r) => r.data),
  dashboard: () => api.get<DashboardStats>('/dashboard/stats').then((r) => r.data),
  startABTest: (modelName: string, payload: { name?: string; control_version_id: number; treatment_version_id: number; traffic_percentage: number }) => api.post<{ test: ABTest }>(`/models/${modelName}/ab-tests`, payload).then((r) => r.data.test),
  abTestResults: (modelName: string, testId: number) => api.get<ABTestResults>(`/models/${modelName}/ab-tests/${testId}/results`).then((r) => r.data),
  endABTest: (modelName: string, testId: number) => api.post<{ test: ABTest }>(`/models/${modelName}/ab-tests/${testId}/end`).then((r) => r.data.test),
  modelVersions: (modelName: string) => api.get<{ model_name: string; versions: ModelVersion[] }>(`/models/${modelName}/versions`).then((r) => r.data.versions),
  activateModelVersion: (modelName: string, versionId: number) => api.post<{ version: ModelVersion }>(`/models/${modelName}/versions/${versionId}/activate`).then((r) => r.data.version),
  abTests: (modelName: string) => api.get<{ tests: ABTest[] }>(`/models/${modelName}/ab-tests`).then((r) => r.data.tests),
};

export interface DashboardStats {
  total: number; approved: number; rejected: number; under_review: number; approval_rate: number | null;
  risk_distribution: { low: number; medium: number; high: number };
  fraud_flag_summary: Array<{ flag: string; count: number }>;
  recent_applications: Array<import('../types').ApplicationDetail['application'] & { prediction: import('../types').PredictionResult | null }>;
}
