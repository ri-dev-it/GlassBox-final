import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import Results from './Results';
import { applicationApi, explanationApi } from '../../services/api';
import type { ApplicationDetail } from '../../types';

vi.mock('../../services/api', () => ({
  applicationApi: { getById: vi.fn(), report: vi.fn() },
  explanationApi: { groundedApplication: vi.fn() },
}));

const detail = {
  application: {
    id: 7,
    application_id: 'APP-2026-0007',
    status: 'REVIEW',
    applicant_id: 2,
    features: {},
    created_at: '2026-04-01T00:00:00',
    loan_type: 'PERSONAL_LOAN',
  },
  prediction: {
    decision: 'REVIEW',
    probability: 0.7,
    risk_score: 40,
    risk_level: 'MEDIUM',
  },
  shap: null,
  lime: null,
  comparison: null,
  counterfactual: null,
  bankEligibility: [],
  documentVerification: {
    verdict: 'VERIFIED',
    checks: [],
    reasons: [],
    identity: {},
    features: {},
    bankStatement: {
      accountHolder: 'Asha Example',
      accountNumber: '******1234',
      bankName: 'Example Bank',
      branch: 'Central',
      ifsc: 'EXAM0000001',
      transactions: [{ date: '2026-03-01', description: 'Monthly Salary', debit: 0, credit: 45000, balance: 65000 }],
      features: { avg_monthly_credits: 45000, salary_regularity: 3 },
      period: { start: '2026-01-01', end: '2026-03-31', observed_days: 90, transaction_count: 1, window_days: 90 },
    },
  },
  transactionReasoning: {
    period: { start: '2026-01-01', end: '2026-03-31', observed_days: 90, transaction_count: 1, window_days: 90 },
    summary: 'Consistent salary credits supported the decision.',
    baselineApprovalProbability: 0.65,
    adjustedApprovalProbability: 0.7,
    probabilityAdjustment: 0.05,
    factors: [{ feature: 'salary_regularity', label: 'Salary regularity', value: 3, adjustment: -0.02, reason: 'Salary credits appeared in three months.' }],
  },
} as unknown as ApplicationDetail;

describe('Results transaction analysis', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(applicationApi.getById).mockResolvedValue(detail);
    vi.mocked(applicationApi.report).mockRejectedValue(new Error('No stored report'));
    vi.mocked(explanationApi.groundedApplication).mockRejectedValue(new Error('No grounded explanation'));
  });

  it('shows the 90-day transaction table, features, and decision impact', async () => {
    render(<MemoryRouter initialEntries={['/results/7']}><Routes><Route path="/results/:id" element={<Results />} /></Routes></MemoryRouter>);
    expect(await screen.findByRole('heading', { name: 'Transaction Analysis' })).toBeTruthy();
    expect(screen.getByText('Monthly Salary')).toBeTruthy();
    expect(screen.getByText('Average monthly credits')).toBeTruthy();
    expect(screen.getByText('Consistent salary credits supported the decision.')).toBeTruthy();
    expect(screen.getByText(/Decision window: 2026-01-01 to 2026-03-31/)).toBeTruthy();
  });
});