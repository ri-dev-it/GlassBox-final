import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import DocumentVerificationSection from './DocumentVerificationSection';
import { documentApi } from '../../services/api';
import type { DocumentRecord, DocumentStatus, DocumentType, VerificationReport } from '../../types';

vi.mock('../../services/api', () => ({ documentApi: { pending: vi.fn(), report: vi.fn(), upload: vi.fn(), remove: vi.fn() } }));
const report: VerificationReport = { verdict: 'NEEDS_REVIEW', identity: { aadhaar: '********7779' }, features: {}, reasons: ['Missing document'],
  checks: [{ name: 'required_document', slot: 'salary_slip', status: 'WARN', reason: 'Missing document', evidence: {} }] };
const ocrNotice = 'Scanned PDFs require Poppler and Tesseract on PATH.';

function documentResult(documentType: DocumentType, status: DocumentStatus, mismatches: string[] = []): DocumentRecord {
  return { id: documentType === 'PAN_CARD' ? 2 : 1, documentType, status, filename: 'document.pdf', documentStatus: 'pending',
    verification: { documentType, status, confidence: 0.9, extractedInformation: {}, mismatches, verificationMessage: 'Processed.' } };
}

function card(title: string) {
  return screen.getByLabelText(new RegExp(`^${title}`)).closest('article')!;
}

function uploadFile(title: string) {
  fireEvent.change(screen.getByLabelText(new RegExp(`^${title}`)), { target: { files: [new File(['dummy'], 'document.pdf', { type: 'application/pdf' })] } });
}

async function ready() {
  await screen.findByLabelText(/^Aadhaar/);
  await waitFor(() => expect((screen.getByLabelText(/^Aadhaar/) as HTMLInputElement).disabled).toBe(false));
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(documentApi.pending).mockResolvedValue([]);
  vi.mocked(documentApi.report).mockResolvedValue(report);
});

describe('Document verification', () => {
  it('does not show verification reason tables on the upload screen', async () => {
    render(<DocumentVerificationSection />);
    await ready();
    expect(screen.queryByText(/Document verification:/)).toBeNull();
    expect(screen.queryByText('Missing document')).toBeNull();
  });
  it('shows wrong-slot reasons returned by upload', async () => {
    const rejected = documentResult('AADHAAR_CARD', 'REJECTED', ['Wrong document type.']);
    vi.mocked(documentApi.upload).mockImplementation(async () => {
      vi.mocked(documentApi.pending).mockResolvedValue([rejected]);
      throw { response: { data: { document: rejected, checks: [{ status: 'FAIL', reason: 'Wrong document type.' }] } } };
    });
    render(<DocumentVerificationSection />);
    await ready();
    const input = screen.getByLabelText(/^Aadhaar/);
    fireEvent.change(input, { target: { files: [new File(['dummy'], 'salary.pdf', { type: 'application/pdf' })] } });
    await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('Wrong document type.'));
    expect(documentApi.upload).toHaveBeenCalled();
    expect(within(card('Aadhaar')).getByText('REJECTED')).toBeTruthy();
    expect(within(card('PAN Card')).getByText('NOT UPLOADED')).toBeTruthy();
    expect(within(card('PAN Card')).queryByRole('alert')).toBeNull();
  });

  it('keeps all empty cards free of verification reasons and capability notices', async () => {
    render(<DocumentVerificationSection />);
    await ready();
    for (const title of ['Aadhaar', 'PAN Card', 'Salary slip', 'Bank statement']) {
      expect(within(card(title)).getByText('NOT UPLOADED')).toBeTruthy();
      expect(card(title).querySelectorAll('p')).toHaveLength(0);
      expect(within(card(title)).queryByRole('button')).toBeNull();
    }
    expect(screen.queryByText(/Poppler|Tesseract/)).toBeNull();
  });

  it.each([ocrNotice, 'OCR requires Tesseract. Install Tesseract and add it to PATH.'])('shows one global capability notice after a real backend failure: %s', async (notice) => {
    vi.mocked(documentApi.upload).mockRejectedValue({ response: { data: { message: notice } } });
    render(<DocumentVerificationSection />);
    await ready();
    for (const title of ['Aadhaar', 'PAN Card']) {
      uploadFile(title);
      await screen.findByText(notice);
      await ready();
      expect(screen.getAllByText(notice)).toHaveLength(1);
      expect(screen.getByText(notice).closest('article')).toBeNull();
      expect(within(card(title)).getByText('NOT UPLOADED')).toBeTruthy();
      expect(card(title).querySelectorAll('p')).toHaveLength(0);
    }
    expect(documentApi.upload).toHaveBeenCalledTimes(2);
  });

  it('deduplicates capability notices in stored records and report checks while preserving real reasons', async () => {
    vi.mocked(documentApi.pending).mockResolvedValue([
      documentResult('AADHAAR_CARD', 'NEEDS_REVIEW', [ocrNotice, 'Document holder name could not be extracted.']),
      documentResult('PAN_CARD', 'NEEDS_REVIEW', [ocrNotice]),
    ]);
    vi.mocked(documentApi.report).mockResolvedValue({ ...report, checks: [
      ...report.checks, { name: 'ocr', slot: 'pan', status: 'WARN', reason: ocrNotice, evidence: {} },
    ], reasons: [ocrNotice] });
    render(<DocumentVerificationSection />);
    await ready();
    expect(screen.getAllByText(ocrNotice)).toHaveLength(1);
    expect(within(card('Aadhaar')).queryByText(ocrNotice)).toBeNull();
    expect(within(card('PAN Card')).queryByText(ocrNotice)).toBeNull();
    expect(within(card('Aadhaar')).getByText('Document holder name could not be extracted.')).toBeTruthy();
  });

  it.each(['VERIFIED', 'NEEDS_REVIEW'] as const)('shows %s and its real reasons only after upload and verification', async (status) => {
    const reasons = status === 'NEEDS_REVIEW' ? ['Document holder name could not be extracted.'] : [];
    const processed = documentResult('PAN_CARD', status, reasons);
    vi.mocked(documentApi.upload).mockImplementation(async () => {
      vi.mocked(documentApi.pending).mockResolvedValue([processed]);
      return processed;
    });
    render(<DocumentVerificationSection />);
    await ready();
    expect(within(card('PAN Card')).getByText('NOT UPLOADED')).toBeTruthy();
    uploadFile('PAN Card');
    await waitFor(() => expect(within(card('PAN Card')).getByText(status)).toBeTruthy());
    await ready();
    for (const reason of reasons) expect(within(card('PAN Card')).getByText(reason)).toBeTruthy();
    expect(within(card('PAN Card')).getByRole('button', { name: 'Remove PAN Card' })).toBeTruthy();
    expect(within(card('Aadhaar')).getByText('NOT UPLOADED')).toBeTruthy();
    expect(card('Aadhaar').querySelectorAll('p')).toHaveLength(0);
  });

  it('does not show a verification outcome before the backend returns verification details', async () => {
    vi.mocked(documentApi.pending).mockResolvedValue([{ ...documentResult('PAN_CARD', 'VERIFIED'), verification: null }]);
    render(<DocumentVerificationSection />);
    await ready();
    expect(within(card('PAN Card')).queryByText('VERIFIED')).toBeNull();
    expect(within(card('PAN Card')).getByText('Uploaded')).toBeTruthy();
  });

  it('shows Uploaded while keeping an identity mismatch visible for review', async () => {
    const uploaded = {
      ...documentResult('SALARY_SLIP', 'UPLOADED'),
      verification: {
        ...documentResult('SALARY_SLIP', 'NEEDS_REVIEW').verification!,
        status: 'NEEDS_REVIEW' as const,
        mismatches: ['The extracted document name does not match the registered account name; administrator review is recommended.'],
      },
    };
    vi.mocked(documentApi.pending).mockResolvedValue([uploaded]);
    render(<DocumentVerificationSection />);
    await ready();
    expect(within(card('Salary slip')).getByText('Uploaded')).toBeTruthy();
    expect(within(card('Salary slip')).getByText(/administrator review is recommended/)).toBeTruthy();
  });

  it('shows Aadhaar approved with a green check after upload despite a missing-name warning', async () => {
    vi.mocked(documentApi.pending).mockResolvedValue([documentResult(
      'AADHAAR_CARD', 'UPLOADED', ['Document holder name could not be extracted; administrator review is recommended.'],
    )]);
    render(<DocumentVerificationSection />);
    await waitFor(() => expect(within(card('Aadhaar')).getByText('Aadhaar approved')).toBeTruthy());
    expect(within(card('Aadhaar')).getByText('Aadhaar approved').className).toContain('bg-green-100');
    expect(within(card('Aadhaar')).getByText('Aadhaar approved').querySelector('svg')).toBeTruthy();
    expect(within(card('Aadhaar')).queryByText(/administrator review is recommended/)).toBeNull();
  });

  it('shows PAN Card approved with a green check after upload despite a missing-name warning', async () => {
    vi.mocked(documentApi.pending).mockResolvedValue([documentResult(
      'PAN_CARD', 'UPLOADED', ['Document holder name could not be extracted; administrator review is recommended.'],
    )]);
    render(<DocumentVerificationSection />);
    await waitFor(() => expect(within(card('PAN Card')).getByText('PAN Card approved')).toBeTruthy());
    expect(within(card('PAN Card')).getByText('PAN Card approved').className).toContain('bg-green-100');
    expect(within(card('PAN Card')).getByText('PAN Card approved').querySelector('svg')).toBeTruthy();
    expect(within(card('PAN Card')).queryByText(/administrator review is recommended/)).toBeNull();
  });

  it('keeps failed upload feedback outside an empty card', async () => {
    vi.mocked(documentApi.upload).mockRejectedValue({ response: { data: { message: 'Only PDF, JPG, and PNG files with valid content are supported.' } } });
    render(<DocumentVerificationSection />);
    await ready();
    uploadFile('PAN Card');
    const alert = await screen.findByRole('alert');
    expect(alert.textContent).toContain('PAN Card: Only PDF');
    expect(alert.closest('article')).toBeNull();
    await ready();
    expect(within(card('PAN Card')).getByText('NOT UPLOADED')).toBeTruthy();
    expect(card('PAN Card').querySelectorAll('p')).toHaveLength(0);
  });

  it('removes a processed document with the existing button and clears its reasons', async () => {
    vi.mocked(documentApi.pending).mockResolvedValue([documentResult('PAN_CARD', 'REJECTED', ['Wrong document type.'])]);
    vi.mocked(documentApi.remove).mockImplementation(async () => {
      vi.mocked(documentApi.pending).mockResolvedValue([]);
      return report;
    });
    render(<DocumentVerificationSection />);
    await ready();
    fireEvent.click(within(card('PAN Card')).getByRole('button', { name: 'Remove PAN Card' }));
    await waitFor(() => expect(within(card('PAN Card')).getByText('NOT UPLOADED')).toBeTruthy());
    expect(documentApi.remove).toHaveBeenCalledWith(2);
    expect(card('PAN Card').querySelectorAll('p')).toHaveLength(0);
  });
});
