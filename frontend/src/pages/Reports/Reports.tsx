import { useEffect, useState } from 'react';
import { FileBarChart } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { AnalysisReport, ApplicationDetail, DocumentRecord } from '../../types';
import { applicationApi, documentApi } from '../../services/api';
import { StatusBadge } from '../../components/common/StatusBadge';
import { FEATURES, formatModelFeatureValue } from '../../utils/featureConfig';

type ApplicationRow = ApplicationDetail['application'] & { prediction: ApplicationDetail['prediction']; applicant?: { full_name: string; email: string } };
type ReportRow = { application: ApplicationRow; report: AnalysisReport | null };

export default function Reports() {
  const [rows, setRows] = useState<ReportRow[]>([]); const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null); const [selected, setSelected] = useState<number | null>(null);
  const [details, setDetails] = useState<Record<number, DocumentRecord[]>>({});
  const [open, setOpen] = useState<Record<number, 'report' | 'form' | null>>({});
  useEffect(() => { let active = true; applicationApi.list().then(async applications => {
    const found = await Promise.all((applications as ApplicationRow[]).filter(a => a.prediction).map(async application => {
      try { return { application, report: await applicationApi.report(application.id) }; }
      catch { return { application, report: null }; }
    })); if (active) setRows(found);
  }).catch(() => { if (active) setError('Could not load reports.'); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; }; }, []);
  const groups = Object.values(rows.reduce<Record<number, { id: number; name: string; email: string; rows: ReportRow[] }>>((all, row) => {
    const id = row.application.applicant_id; const applicant = row.application.applicant;
    (all[id] ??= { id, name: applicant?.full_name ?? `Applicant ${id}`, email: applicant?.email ?? '', rows: [] }).rows.push(row); return all;
  }, {}));
  const current = groups.find(group => group.id === selected);
  const toggle = async (applicationId: number, tab: 'report' | 'form') => {
    if (tab === 'form' && !details[applicationId]) { const detail = await applicationApi.getById(applicationId); setDetails(prev => ({ ...prev, [applicationId]: detail.documents ?? [] })); }
    setOpen(prev => ({ ...prev, [applicationId]: prev[applicationId] === tab ? null : tab }));
  };
  if (loading) return <p className="text-sm text-slate-500">Loading reports...</p>;
  if (error) return <p className="text-sm text-red-700">{error}</p>;
  if (!rows.length) return <div className="rounded-xl border border-dashed border-slate-300 p-10 text-center"><FileBarChart className="mx-auto text-slate-400"/><h1 className="mt-3 text-xl font-semibold text-slate-800">No reports yet</h1><p className="mt-1 text-sm text-slate-500">Stored reports will appear after a completed assessment.</p></div>;
  if (current) return <div className="space-y-6"><button onClick={() => setSelected(null)} className="text-sm font-semibold text-brand-700">← All applicants</button><div><p className="eyebrow">Applicant report</p><h1 className="text-3xl font-bold text-slate-900">{current.name}</h1><p className="text-sm text-slate-500">{current.email}</p><p className="mt-1 text-sm text-slate-600">{current.rows.length} applications</p></div>
    {current.rows.map(({ application, report }, index) => <section key={application.id} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex justify-between"><div><h2 className="font-semibold">Application {index + 1}: {application.loan_type?.replaceAll('_', ' ')}</h2><p className="text-sm text-slate-500">{application.application_id} · {new Date(application.created_at).toLocaleDateString()}</p></div><StatusBadge value={application.admin_decision ?? report?.decision ?? application.status}/></div>
      <div className="mt-4 flex gap-2"><button onClick={() => toggle(application.id, 'report')} className="rounded-md border px-3 py-2 text-sm">Report</button><button onClick={() => toggle(application.id, 'form')} className="rounded-md border px-3 py-2 text-sm">Submitted Form</button></div>
      {open[application.id] === 'report' && <div className="mt-4 rounded-lg bg-slate-50 p-4"><h3 className="font-semibold">AI generated report</h3>{report ? <><p className="mt-2 text-sm text-slate-600">Decision {report.decision} · Risk score {report.risk.score}/100 · {Math.round(report.probability * 100)}% approval probability</p><p className="mt-2 text-sm text-slate-600">{report.lime.summary}</p></> : <p className="mt-2 text-sm">Report unavailable.</p>}<Link className="mt-3 inline-block text-sm font-semibold text-brand-700" to={`/results/${application.id}`}>Open full assessment</Link></div>}
      {open[application.id] === 'form' && <div className="mt-4 space-y-4 rounded-lg bg-slate-50 p-4"><h3 className="font-semibold">Submitted Form · Read only</h3>{(['Applicant','Financial','Loan','Assets'] as const).map(section => <div key={section}><h4 className="font-medium">{section} Information</h4><dl className="mt-2 grid gap-2 text-sm md:grid-cols-2">{Object.entries(application.features).filter(([key]) => FEATURES[key]?.section === section).map(([key, value]) => <div key={key} className="rounded bg-white p-2"><dt className="text-slate-500">{FEATURES[key].label}</dt><dd className="font-medium">{FEATURES[key].optionLabels?.[String(value)] ?? formatModelFeatureValue(key, value)}</dd></div>)}</dl></div>)}
        {Object.entries(application.features).some(([key]) => !FEATURES[key] && key !== 'loan_type') && <div><h4 className="font-medium">Loan-specific Information</h4><dl className="mt-2 grid gap-2 text-sm md:grid-cols-2">{Object.entries(application.features).filter(([key]) => !FEATURES[key] && key !== 'loan_type').map(([key,value]) => <div key={key} className="rounded bg-white p-2"><dt className="text-slate-500">{key.replaceAll('_',' ')}</dt><dd className="font-medium">{String(value)}</dd></div>)}</dl></div>}
        <div><h4 className="font-medium">Documents</h4>{details[application.id]?.length ? <div className="mt-2 flex flex-wrap gap-3">{details[application.id].map((doc: DocumentRecord) => <a key={doc.id} href={documentApi.fileUrl(doc.id)} target="_blank" rel="noreferrer" className="text-sm font-semibold text-brand-700">{doc.documentType.replaceAll('_',' ')} · {doc.filename}</a>)}</div> : <p className="mt-2 text-sm text-slate-500">No documents submitted for this application.</p>}</div></div>}</section>)}</div>;
  return <div className="space-y-6"><div><p className="eyebrow">Assessment archive</p><h1 className="mt-1 text-3xl font-bold text-slate-900">Reports</h1><p className="mt-2 text-sm text-slate-500">One entry per applicant. Open an applicant to review each application.</p></div><div className="grid gap-4 md:grid-cols-3">{groups.map(group => { const latest = group.rows[0]?.report; const latestApp = group.rows[0]?.application; return <button key={group.id} onClick={() => setSelected(group.id)} className="rounded-xl border border-slate-200 bg-white p-5 text-left shadow-sm hover:border-brand-400"><h2 className="font-semibold text-slate-900">{group.name}</h2><p className="mt-1 text-sm text-slate-500">{group.email}</p><p className="mt-3 text-sm text-slate-600">{group.rows.length} applications</p><p className="mt-2 text-sm text-slate-700">Latest: {latestApp?.loan_type?.replaceAll('_',' ')} · {latestApp?.admin_decision ?? latest?.decision ?? latestApp?.status}</p></button>; })}</div></div>;
}
