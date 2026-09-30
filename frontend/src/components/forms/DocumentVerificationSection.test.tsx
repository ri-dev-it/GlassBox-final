import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import DocumentVerificationSection from './DocumentVerificationSection';
import VerificationReportView from './VerificationReportView';
import { documentApi } from '../../services/api';
import type { VerificationReport } from '../../types';

vi.mock('../../services/api', () => ({ documentApi: { pending: vi.fn(), report: vi.fn(), upload: vi.fn() } }));
const report: VerificationReport = { verdict: 'NEEDS_REVIEW', identity: { aadhaar: '********7779' }, features: {}, reasons: ['Missing document'],
  checks: [{ name: 'required_document', slot: 'salary_slip', status: 'WARN', reason: 'Missing document', evidence: {} }] };

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(documentApi.pending).mockResolvedValue([]);
  vi.mocked(documentApi.report).mockResolvedValue(report);
});

describe('Document verification', () => {
  it('renders a masked identity and check status', () => {
    render(<VerificationReportView report={report} />);
    expect(screen.getByText('Aadhaar: ********7779')).toBeTruthy();
    expect(screen.getByText('WARN')).toBeTruthy();
  });
  it('shows wrong-slot reasons returned by upload', async () => {
    vi.mocked(documentApi.upload).mockRejectedValue({ response: { data: { checks: [{ status: 'FAIL', reason: 'Wrong document type.' }] } } });
    render(<DocumentVerificationSection />);
    const input = screen.getByLabelText('Aadhaar');
    fireEvent.change(input, { target: { files: [new File(['dummy'], 'salary.pdf', { type: 'application/pdf' })] } });
    await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('Wrong document type.'));
    expect(documentApi.upload).toHaveBeenCalled();
  });
});
