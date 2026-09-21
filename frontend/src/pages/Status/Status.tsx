import { useEffect, useState } from 'react';
import { applicationApi } from '../../services/api';
import type { ApplicationDetail } from '../../types';
import { StatusBadge } from '../../components/common/StatusBadge';
import { formatINR } from '../../utils/featureConfig';

type Row = ApplicationDetail['application'] & { prediction: ApplicationDetail['prediction'] };

export default function Status() {
  const [apps, setApps] = useState<Row[]>([]);
  const [query, setQuery] = useState('');
  useEffect(() => { applicationApi.list().then((items) => setApps(items as Row[])); }, []);

  const app = apps.find((item) => item.application_id.toLowerCase() === query.trim().toLowerCase()) ?? (query ? undefined : apps[0]);
  const finalDecision = app?.admin_decision ?? app?.prediction?.decision;
  const finalStep = finalDecision === 'APPROVE' || finalDecision === 'APPROVED'
    ? 'Final decision: approved'
    : finalDecision === 'REJECT' || finalDecision === 'REJECTED' || finalDecision === 'DECLINE'
      ? 'Final decision: rejected'
      : 'Final decision pending';

  return <div className="mx-auto max-w-3xl">
    <p className="text-sm font-medium text-sky-700">Track application</p>
    <h1 className="mt-1 text-3xl font-bold text-[#102a4c]">Application Status</h1>
    <p className="mt-2 text-slate-500">Search an application ID to view its assessment timeline.</p>
    <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search e.g. APP-2026-0001" className="mt-6 w-full rounded-lg border border-slate-300 bg-white px-4 py-3 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100" />
    {query && !app && <p className="mt-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-800">No matching application was found.</p>}
    {app && <section className="mt-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-wrap justify-between gap-3"><div><p className="text-sm text-slate-500">{app.application_id}</p><h2 className="mt-1 text-xl font-semibold text-slate-800">Loan Assessment</h2></div><StatusBadge value={finalDecision ?? 'Under Review'} /></div>
      <dl className="mt-6 grid gap-4 border-y border-slate-100 py-5 sm:grid-cols-3"><div><dt className="text-xs uppercase tracking-wide text-slate-400">Loan amount</dt><dd className="mt-1 font-semibold text-slate-700">{formatINR(Number(app.features.credit_amount) * 100)}</dd></div><div><dt className="text-xs uppercase tracking-wide text-slate-400">Risk level</dt><dd className="mt-1">{app.prediction && <StatusBadge value={app.prediction.risk_level} />}</dd></div><div><dt className="text-xs uppercase tracking-wide text-slate-400">Next step</dt><dd className="mt-1 text-sm font-medium text-slate-700">View your AI assessment</dd></div></dl>
      <ol className="mt-6 space-y-5">{['Application submitted', 'Information review', 'AI credit assessment', finalStep].map((step, index) => <li className="flex gap-3" key={step}><span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-xs font-bold text-emerald-700">{index + 1}</span><span className="pt-0.5 text-sm text-slate-700">{step}</span></li>)}</ol>
    </section>}
  </div>;
}
