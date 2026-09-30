import { useEffect, useState } from 'react';
import { documentApi } from '../../services/api';
import type { DocumentRecord, DocumentType, VerificationReport } from '../../types';
import VerificationReportView from './VerificationReportView';

const SLOTS: Array<{ type: DocumentType; title: string }> = [
  { type: 'AADHAAR_CARD', title: 'Aadhaar' }, { type: 'SALARY_SLIP', title: 'Salary slip' },
  { type: 'BANK_STATEMENT', title: 'Bank statement' }, { type: 'EMPLOYMENT_INCOME_PROOF', title: 'Income certificate' },
];

export default function DocumentVerificationSection() {
  const [documents, setDocuments] = useState<Record<string, DocumentRecord>>({});
  const [report, setReport] = useState<VerificationReport | null>(null);
  const [uploading, setUploading] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const refresh = async () => {
    const [docs, verification] = await Promise.all([documentApi.pending(), documentApi.report()]);
    setDocuments(Object.fromEntries(docs.map(d => [d.documentType, d])));
    setReport(verification);
  };
  useEffect(() => { refresh().catch(() => setErrors({ general: 'Could not load document report.' })); }, []);
  const upload = async (type: DocumentType, file?: File) => {
    if (!file) return;
    setErrors(prev => ({ ...prev, [type]: '' }));
    if (file.size > 5 * 1024 * 1024) {
      setErrors(prev => ({ ...prev, [type]: 'Maximum file size is 5 MB.' })); return;
    }
    setUploading(type); setProgress(0);
    try {
      await documentApi.upload(type, file, true, setProgress);
    } catch (error: unknown) {
      const data = (error as { response?: { data?: { message?: string; checks?: Array<{ status: string; reason: string }> } } }).response?.data;
      const reasons = data?.checks?.filter(c => c.status !== 'PASS').map(c => c.reason).join(' ');
      setErrors(prev => ({ ...prev, [type]: reasons || data?.message || 'Upload failed. Please try again.' }));
    } finally {
      await refresh().catch(() => setErrors(prev => ({ ...prev, general: 'Could not refresh document report.' })));
      setUploading(null);
    }
  };
  return <section className="rounded-xl border border-slate-200 bg-white p-5">
    <h2 className="text-lg font-semibold">Upload documents</h2>
    <p className="mt-2 text-sm text-slate-500">Start with Aadhaar to establish your identity. PDF, PNG or JPG, up to 5 MB. Aadhaar is retained only as a masked summary.</p>
    {errors.general && <p role="alert">{errors.general}</p>}
    <div className="mt-5 grid gap-4 md:grid-cols-2">{SLOTS.map(({ type, title }) => {
      const document = documents[type];
      return <article key={type} className="rounded-lg border p-4">
        <div className="flex justify-between gap-2"><label htmlFor={`upload-${type}`} className="font-semibold">{title}</label>
          <span className="rounded bg-slate-100 px-2 text-xs">{document?.status ?? 'NOT UPLOADED'}</span></div>
        <input id={`upload-${type}`} type="file" accept=".pdf,.png,.jpg,.jpeg" disabled={!!uploading}
          className="mt-3 block w-full text-sm" onChange={event => { void upload(type, event.target.files?.[0]); event.target.value = ''; }} />
        {uploading === type && <div className="mt-2"><progress aria-label={`${title} upload progress`} max={100} value={progress} /><p className="text-xs">{progress < 100 ? `${progress}% uploaded` : 'Extracting and checking document…'}</p></div>}
        {errors[type] && <p role="alert" className="mt-2 text-sm text-red-700">{errors[type]}</p>}
        {document?.verification?.mismatches.map((reason, i) => <p key={i} className="mt-2 text-xs text-amber-800">{reason}</p>)}
      </article>;
    })}</div>
    {report && <VerificationReportView report={report} />}
  </section>;
}
