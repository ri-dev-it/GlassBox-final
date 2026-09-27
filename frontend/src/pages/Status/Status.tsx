import { useEffect, useState } from 'react';
import { ArrowLeft, Check, Circle, X } from 'lucide-react';
import { applicationApi } from '../../services/api';
import type { ApplicationDetail, LoanType } from '../../types';
import { StatusBadge } from '../../components/common/StatusBadge';
import { formatINR } from '../../utils/featureConfig';

type Row = ApplicationDetail['application'] & { prediction: ApplicationDetail['prediction'] };
const STAGES = ['Form submitted', 'Information / form review', 'Document verification', 'AI credit assessment', 'Manual review (underwriter)', 'Final decision'] as const;

function getOutcome(app: Row): 'APPROVED' | 'REJECTED' | 'REVIEW' {
  const decision = app.admin_decision ?? app.prediction?.decision;
  if (decision === 'APPROVE' || decision === 'APPROVED') return 'APPROVED';
  if (decision === 'REJECT' || decision === 'REJECTED' || decision === 'DECLINE') return 'REJECTED';
  return 'REVIEW';
}

function loanName(type?: LoanType) {
  return type?.replaceAll('_', ' ').replace(/\b\w/g, character => character.toUpperCase()) ?? 'Loan application';
}

export default function Status() {
  const [apps, setApps] = useState<Row[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { applicationApi.list().then(items => setApps(items as Row[])).catch(() => setError('Could not load your applications.')); }, []);

  const app = apps.find(item => item.id === selectedId);
  const outcome = app ? getOutcome(app) : 'REVIEW';
  const isFinal = outcome !== 'REVIEW';
  const finalStageText = outcome === 'APPROVED' ? 'Final decision — Approved' : outcome === 'REJECTED' ? 'Final decision — Rejected' : 'Final decision — Pending';

  return <div className="mx-auto max-w-3xl">
    <p className="text-sm font-medium text-sky-700">Track application</p>
    <h1 className="mt-1 text-3xl font-bold text-brand-900">Application Status</h1>
    {error && <p role="alert" className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    {!app ? <div className="mt-6 space-y-3">{apps.length ? apps.map(item => <button key={item.id} type="button" onClick={() => setSelectedId(item.id)} className="w-full rounded-xl border border-slate-200 bg-white p-5 text-left shadow-sm transition hover:border-brand-400"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="font-semibold text-slate-900">{loanName(item.loan_type)}</h2><p className="mt-1 text-sm text-slate-500">{item.application_id} · Applied {item.created_at ? new Date(item.created_at).toLocaleDateString() : 'date unavailable'}</p></div><StatusBadge value={getOutcome(item)} /></div></button>) : !error && <p className="mt-6 rounded-xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">No applications found.</p>}</div> : <section className="mt-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <button type="button" onClick={() => setSelectedId(null)} className="inline-flex items-center gap-2 text-sm font-semibold text-brand-700 hover:underline"><ArrowLeft size={16}/> All applications</button>
      <div className="mt-4 flex flex-wrap justify-between gap-3"><div><p className="text-sm text-slate-500">{app.application_id}</p><h2 className="mt-1 text-xl font-semibold text-slate-800">{loanName(app.loan_type)}</h2></div><StatusBadge value={outcome} /></div>
      <dl className="mt-6 grid gap-4 border-y border-slate-100 py-5 sm:grid-cols-2"><div><dt className="text-xs uppercase tracking-wide text-slate-400">Loan amount</dt><dd className="mt-1 font-semibold text-slate-700">{formatINR(Number(app.features.credit_amount) * 100)}</dd></div><div><dt className="text-xs uppercase tracking-wide text-slate-400">Risk level</dt><dd className="mt-1">{app.prediction ? <StatusBadge value={app.prediction.risk_level} /> : <span className="text-sm text-slate-500">Pending</span>}</dd></div></dl>
      <ol className="mt-6">
        {STAGES.map((stage, index) => {
          const terminal = index === 5;
          const completed = terminal ? isFinal : index === 0 || isFinal || (!!app.prediction && index < 4);
          const rejected = terminal && outcome === 'REJECTED';
          const label = terminal ? finalStageText : stage;
          return <li key={stage} className="relative flex gap-4 pb-7 last:pb-0"><span aria-hidden="true" className={`absolute left-[15px] top-8 h-[calc(100%-1rem)] w-px last:hidden ${completed ? 'bg-emerald-300' : 'bg-slate-200'}`} />
            <span className={`relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${rejected ? 'bg-red-100 text-red-700' : completed ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-400'}`}>{rejected ? <X size={17} aria-label="Rejected" /> : completed ? <Check size={17} aria-label="Completed" /> : <Circle size={14} aria-label="Pending" />}</span>
            <div className={`pt-1 ${completed ? 'text-slate-800' : 'text-slate-400'}`}><h3 className="text-sm font-semibold">{label}</h3>{terminal && outcome === 'REJECTED' && <p className="mt-1 text-sm text-slate-600">Reason: {app.admin_feedback || 'No additional reason was provided.'}</p>}{terminal && outcome === 'APPROVED' && app.admin_feedback && <p className="mt-1 text-sm text-slate-600">Note: {app.admin_feedback}</p>}</div>
          </li>;
        })}
      </ol>
    </section>}
  </div>;
}
