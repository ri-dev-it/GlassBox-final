import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import Reports from './Reports';
import { applicationApi, documentApi } from '../../services/api';
import type { ApplicationDetail, BankStatementDetail } from '../../types';

vi.mock('../../services/api', () => ({
  applicationApi: { list: vi.fn(), report: vi.fn(), getById: vi.fn() },
  documentApi: { preview: vi.fn() },
}));

const statement: BankStatementDetail = {
  accountHolder: 'Asha Example',
  accountNumber: '******1234',
  bankName: 'Example Bank',
  branch: 'Central',
  ifsc: 'EXAM0000001',
  transactions: [{ date: '2026-03-01', description: 'Monthly Salary', debit: 0, credit: 45000, balance: 65000 }],
  features: { avg_monthly_credits: 45000, salary_regularity: 3 },
  period: { start: '2026-01-01', end: '2026-03-31', observed_days: 90, transaction_count: 1, window_days: 90 },
};

const application = {
  id: 7,
  application_id: 'APP-2026-0007',
  applicant_id: 2,
  status: 'REVIEW',
  loan_type: 'PERSONAL_LOAN',
  created_at: '2026-04-01T00:00:00',
  admin_decision: null,
  features: {},
  applicant: { full_name: 'Asha Example', email: 'asha@example.test' },
  prediction: { decision: 'REVIEW', probability: 0.7 },
} as ApplicationDetail['application'] & { prediction: NonNullable<ApplicationDetail['prediction']>; applicant: { full_name: string; email: string } };

const analysisReport = {
  decision: 'REVIEW',
  probability: 0.7,
  risk: { score: 40 },
  lime: { summary: 'Income history considered.' },
} as never;

const detail = {
  application,
  prediction: application.prediction,
  documentVerification: { verdict: 'VERIFIED', checks: [], reasons: [], identity: {}, features: {}, bankStatement: statement },
  transactionReasoning: {
    period: statement.period,
    summary: 'Monthly salary credits supported the decision.',
    baselineApprovalProbability: 0.65,
    adjustedApprovalProbability: 0.7,
    probabilityAdjustment: 0.05,
    factors: [],
  },
  documents: [{ id: 22, documentType: 'BANK_STATEMENT', filename: 'statement.pdf' }],
} as unknown as ApplicationDetail;

describe('Reports transaction analysis', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(applicationApi.list).mockResolvedValue([application]);
    vi.mocked(applicationApi.report).mockResolvedValue(analysisReport);
    vi.mocked(applicationApi.getById).mockResolvedValue(detail);
    vi.mocked(documentApi.preview).mockResolvedValue(undefined);
  });

  it('shows statement transactions, features, reasoning, and its PDF preview action', async () => {
    render(<MemoryRouter><Reports /></MemoryRouter>);
    fireEvent.click(await screen.findByRole('button', { name: /Asha Example/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Submitted Form' }));

    expect(await screen.findByText('Transaction Analysis')).toBeTruthy();
    expect(screen.getByText('Monthly Salary')).toBeTruthy();
    expect(screen.getByText(/Average monthly credits/)).toBeTruthy();
    expect(screen.getByText('Monthly salary credits supported the decision.')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: /BANK STATEMENT.*statement.pdf/ }));
    await waitFor(() => expect(documentApi.preview).toHaveBeenCalledWith(22));
  });
});