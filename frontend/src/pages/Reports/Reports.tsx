import { useEffect, useState } from 'react';
import { FileBarChart } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { AnalysisReport, ApplicationDetail } from '../../types';
import { applicationApi } from '../../services/api';
import { StatusBadge } from '../../components/common/StatusBadge';

type ApplicationRow = ApplicationDetail['application'] & { prediction: ApplicationDetail['prediction'] };
type ReportRow = { application: ApplicationRow; report: AnalysisReport | null };

export default function Reports() {
  const [rows, setRows] = useState<ReportRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    applicationApi.list()
      .then(async (applications) => {
        const completed = applications as ApplicationRow[];
        const reportRows = await Promise.all(completed.filter((application) => application.prediction).map(async (application) => {
          try {
            return { application, report: await applicationApi.report(application.id) };
          } catch {
            return { application, report: null };
          }
        }));
        if (active) setRows(reportRows);
      })
      .catch(() => { if (active) setError('Could not load reports.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const groups = Object.values(rows.reduce<Record<string, { name: string; email: string; rows: ReportRow[] }>>((all, row) => { const applicant = (row.application as ApplicationRow & { applicant?: { full_name: string; email: string } }).applicant; const key = applicant?.email ?? `applicant-${row.application.applicant_id}`; (all[key] ??= { name: applicant?.full_name ?? `Applicant ${row.application.applicant_id}`, email: key, rows: [] }).rows.push(row); return all; }, {}));
  const current = groups.find(group => group.email === selected);

  if (loading) return <p className="text-sm text-slate-500">Loading reports...</p>;
  if (error) return <p className="text-sm text-red-700">{error}</p>;
  if (!rows.length) return <div className="rounded-xl border border-dashed border-slate-300 p-10 text-center"><FileBarChart className="mx-auto text-slate-400" /><h1 className="mt-3 text-xl font-semibold text-slate-800">No reports yet</h1><p className="mt-1 text-sm text-slate-500">Stored reports will appear after a completed assessment.</p></div>;

  if (current) return <div className="space-y-6"><button onClick={() => setSelected(null)} className="text-sm font-semibold text-brand-700">← All applicants</button><div><p className="eyebrow">Applicant report</p><h1 className="text-3xl font-bold text-slate-900">{current.name}</h1><p className="text-sm text-slate-500">{current.email}</p></div>{current.rows.map(({ application, report }) => <section key={application.id} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex justify-between"><div><h2 className="font-semibold">{application.application_id}</h2><p className="text-sm text-slate-500">{application.loan_type?.replaceAll('_', ' ')}</p></div>{report && <StatusBadge value={report.decision}/>}</div><h3 className="mt-4 font-medium">Raw submitted form data</h3><dl className="mt-2 grid gap-2 text-sm md:grid-cols-2">{Object.entries(application.features).map(([key, value]) => <div key={key} className="rounded bg-slate-50 p-2"><dt className="text-slate-500">{key.replaceAll('_', ' ')}</dt><dd className="font-medium">{typeof value === 'object' ? JSON.stringify(value) : String(value)}</dd></div>)}</dl>{report && <><h3 className="mt-4 font-medium">Assessment</h3><p className="text-sm text-slate-600">Risk score {report.risk.score}/100 · {Math.round(report.probability * 100)}% approval probability</p><p className="mt-2 text-sm text-slate-600">{report.lime.summary}</p></>}<Link className="mt-4 inline-block text-sm font-semibold text-brand-700" to={`/results/${application.id}`}>Open full assessment</Link></section>)}</div>;
  return <div className="space-y-6"><div><p className="eyebrow">Assessment archive</p><h1 className="mt-1 text-3xl font-bold text-slate-900">Reports</h1><p className="mt-2 text-sm text-slate-500">Select an applicant to open their completed assessments and raw submission.</p></div><div className="grid gap-4 md:grid-cols-3">{groups.map(group => { const latest = group.rows[0]?.report; return <button key={group.email} onClick={() => setSelected(group.email)} className="rounded-xl border border-slate-200 bg-white p-5 text-left shadow-sm hover:border-brand-400"><h2 className="font-semibold text-slate-900">{group.name}</h2><p className="mt-1 text-sm text-slate-500">{group.rows.length} completed assessment{group.rows.length === 1 ? '' : 's'}</p><p className="mt-4 text-sm text-slate-700">{latest ? `${latest.decision} · ${latest.risk.level} risk` : 'Report unavailable'}</p></button>; })}</div></div>;
}

