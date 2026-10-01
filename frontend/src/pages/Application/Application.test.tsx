import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import Application from './Application';
import { applicationApi, documentApi } from '../../services/api';
import { FEATURES, FEATURE_KEYS } from '../../utils/featureConfig';
import type { DocumentRecord, DocumentType } from '../../types';

const { navigate } = vi.hoisted(() => ({ navigate: vi.fn() }));
vi.mock('react-router-dom', async importOriginal => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return { ...actual, useNavigate: () => navigate };
});
vi.mock('../../services/api', () => ({
  applicationApi: { submit: vi.fn() },
  documentApi: { pending: vi.fn(), report: vi.fn(), upload: vi.fn(), remove: vi.fn() },
}));

describe('New application submission', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    let uploaded: DocumentRecord[] = [];
    vi.mocked(documentApi.pending).mockImplementation(async () => uploaded);
    vi.mocked(documentApi.report).mockResolvedValue({
      verdict: 'VERIFIED', checks: [], reasons: [], identity: {}, features: {},
      canSubmit: false, submissionErrors: ['stale server report'],
    });
    vi.mocked(documentApi.upload).mockImplementation(async (type: DocumentType, file: File) => {
      const doc: DocumentRecord = {
        id: uploaded.length + 1, documentType: type, status: 'VERIFIED', filename: file.name,
        documentStatus: 'pending',
        verification: { documentType: type, status: 'VERIFIED', confidence: 0, extractedInformation: {}, mismatches: [], verificationMessage: 'Approved.' },
      };
      uploaded = [...uploaded.filter(item => item.documentType !== type), doc];
      return doc;
    });
    vi.mocked(applicationApi.submit).mockResolvedValue({ application: { id: 42 } } as never);
  });

  it('enables from four approved document records and submits on click', async () => {
    render(<MemoryRouter><Application /></MemoryRouter>);
    const analyze = screen.getByRole('button', { name: 'Analyze Application' });
    await waitFor(() => expect(documentApi.pending).toHaveBeenCalled());
    expect((analyze as HTMLButtonElement).disabled).toBe(true);

    for (const [type, title] of [
      ['AADHAAR_CARD', 'Aadhaar'], ['PAN_CARD', 'PAN Card'],
      ['SALARY_SLIP', 'Salary slip'], ['BANK_STATEMENT', 'Bank statement'],
    ] as const) {
      fireEvent.change(screen.getByLabelText(new RegExp(`^${title}`)), {
        target: { files: [new File(['sample'], `${type}.pdf`, { type: 'application/pdf' })] },
      });
      await waitFor(() => expect(withinCard(title).textContent).toContain('Approved'));
    }
    await waitFor(() => expect((analyze as HTMLButtonElement).disabled).toBe(false));

    for (const key of FEATURE_KEYS) {
      const control = document.getElementById(key) as HTMLInputElement | HTMLSelectElement;
      const value = FEATURES[key].category === 'numeric'
        ? String(FEATURES[key].min ?? 1)
        : control instanceof HTMLSelectElement ? control.options[1].value : '';
      fireEvent.change(control, { target: { value } });
    }
    fireEvent.change(screen.getByLabelText('Purpose of loan'), { target: { value: 'Guide review' } });

    fireEvent.click(analyze);
    await waitFor(() => expect(applicationApi.submit).toHaveBeenCalledTimes(1));
    expect(navigate).toHaveBeenCalledWith('/results/42');
  });
});

function withinCard(title: string) {
  return screen.getByLabelText(new RegExp(`^${title}`)).closest('article')!;
}
