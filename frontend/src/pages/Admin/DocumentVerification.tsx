import { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, ExternalLink } from 'lucide-react';
import { documentApi } from '../../services/api';
import type { DocumentRecord, LoanType } from '../../types';
import BankStatementDocument from '../../components/forms/BankStatementDocument';

type ApplicationInfo = {
  id: number;
  application_id: string;
  created_at: string | null;
  loan_type: LoanType | string;
  decision?: string | null;
};
type Row = DocumentRecord & {
  applicant?: { id: number | null; full_name: string; email: string };
  application?: ApplicationInfo | null;
};
type ApplicationGroup = { application: ApplicationInfo | null; docs: Row[] };

export default function DocumentVerification() {
  const [documents, setDocuments] = useState<Row[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const load = () => documentApi.pending().then(rows => setDocuments(rows as Row[])).catch(e => setError(e?.response?.data?.error ?? 'Could not load document verification records.'));
  useEffect(() => { load(); }, []);
  const applicants = useMemo(() => Object.values(documents.reduce<Record<string, { name: string; email: string; docs: Row[] }>>((all, doc) => {
    const key = doc.applicant?.email ?? 'unknown';
    (all[key] ??= { name: doc.applicant?.full_name ?? 'Applicant', email: key, docs: [] }).docs.push(doc);
    return all;
  }, {})), [documents]);
  const applicant = applicants.find(group => group.email === selected);
  const applicationGroups = useMemo<ApplicationGroup[]>(() => {
    if (!applicant) return [];
    const byApplication = new Map<string, ApplicationGroup>();
    applicant.docs.forEach(doc => {
      const key = doc.application ? String(doc.application.id) : 'unknown';
      const group = byApplication.get(key) ?? { application: doc.application ?? null, docs: [] };
      group.docs.push(doc);
      byApplication.set(key, group);
    });
    return [...byApplication.values()].sort((a, b) => (b.application?.created_at ?? '').localeCompare(a.application?.created_at ?? ''));
  }, [applicant]);
  const review = async (id: number, documentStatus: 'approved' | 'rejected') => { await documentApi.review(id, documentStatus); load(); };
  const preview = async (id: number) => { setPreviewError(null); try { await documentApi.preview(id); } catch (e) { setPreviewError(e instanceof Error ? e.message : 'Could not preview this document.'); } };
  const documentCard = (doc: Row) => <article key={doc.id} className={`rounded-xl border border-slate-200 bg-white p-5 shadow-sm ${doc.documentType === 'BANK_STATEMENT' ? 'md:col-span-2' : ''}`}><div className="flex items-center justify-between gap-2"><h3 className="font-semibold text-slate-800">{doc.documentType.replaceAll('_', ' ')}</h3><span className="rounded bg-green-100 px-2 py-1 text-xs font-semibold text-green-800">{doc.status === 'VERIFIED' ? 'Approved ✓' : doc.status.replaceAll('_', ' ')}</span></div><p className="mt-1 text-sm text-slate-500">{doc.filename}</p><p className="mt-3 text-sm text-slate-600">{doc.verification?.verificationMessage ?? 'Awaiting automated check.'}</p>{doc.verification?.mismatches.length ? <ul className="mt-2 space-y-1 text-xs text-amber-800">{doc.verification.mismatches.map((reason, index) => <li key={index}>{reason}</li>)}</ul> : null}<button type="button" className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-brand-700" onClick={() => preview(doc.id)}><ExternalLink size={15}/> Preview</button><div className="mt-4 flex gap-2"><button onClick={() => review(doc.id, 'approved')} className="rounded-md bg-emerald-600 px-3 py-2 text-sm font-semibold text-white">Approve</button><button onClick={() => review(doc.id, 'rejected')} className="rounded-md bg-red-600 px-3 py-2 text-sm font-semibold text-white">Reject</button></div><p className="mt-3 text-xs capitalize text-slate-500">Human review: {doc.documentStatus ?? 'pending'}</p>{doc.documentType === 'BANK_STATEMENT' && <BankStatementDocument documentId={doc.id} />}</article>;

  if (applicant) return <div className="space-y-6"><button onClick={() => setSelected(null)} className="inline-flex items-center gap-2 text-sm font-semibold text-brand-700"><ArrowLeft size={16}/> All applicants</button><div><h1 className="text-3xl font-bold text-slate-900">{applicant.name}'s documents</h1><p className="mt-1 text-sm text-slate-500">{applicant.email}</p></div>{previewError && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{previewError}</p>}{applicationGroups.map((group, index) => {
    const application = group.application;
    return <section key={application?.id ?? `unknown-${index}`} className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><header className="border-b border-slate-100 pb-4"><p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{application?.application_id ?? 'Application details unavailable'}</p><h2 className="mt-1 text-lg font-semibold text-slate-900">{applicant.name}</h2><div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-sm text-slate-600"><span>Submitted: {application?.created_at ? new Date(application.created_at).toLocaleDateString() : 'Date unavailable'}</span><span>Loan type: {application?.loan_type?.replaceAll('_', ' ') ?? 'Unavailable'}</span><span>Decision: {application?.decision ?? 'Pending'}</span></div></header><div className="grid gap-4 md:grid-cols-2">{group.docs.map(documentCard)}</div></section>;
  })}</div>;

  return <div className="space-y-6"><div><p className="eyebrow">Admin / Verification</p><h1 className="mt-1 text-3xl font-bold text-slate-900">Document verification</h1><p className="mt-2 text-slate-500">Select an applicant to review documents grouped by application.</p></div>{error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}<div className="grid gap-4 md:grid-cols-2">{applicants.map(group => <button key={group.email} onClick={() => setSelected(group.email)} className="rounded-xl border border-slate-200 bg-white p-5 text-left shadow-sm hover:border-brand-400"><h2 className="font-semibold text-slate-900">{group.name}</h2><p className="mt-1 text-sm text-slate-500">{group.email}</p><p className="mt-4 text-sm text-slate-600">{group.docs.length} documents submitted · {group.docs.every(doc => doc.documentStatus === 'approved') ? 'Approved' : 'Pending review'}</p></button>)}</div>{!applicants.length && <p className="rounded-xl border border-dashed p-8 text-center text-sm text-slate-500">No submitted documents require review.</p>}</div>;
}
