import { useEffect, useState } from 'react';
import { CheckCircle2, ClipboardList, FileCheck2, XCircle } from 'lucide-react';
import { Link } from 'react-router-dom';
import { adminApi } from '../../services/api';
import type { AdminOverview } from '../../types';

export default function Admin() {
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { adminApi.overview().then(setOverview).catch((requestError) => setError(requestError?.response?.data?.error ?? 'Could not load the admin overview.')); }, []);
  const cards = overview ? [
    { label: 'Pending review', value: overview.pending_review, icon: ClipboardList, tone: 'text-amber-700 bg-amber-50' },
    { label: 'Approved today', value: overview.approved_today, icon: CheckCircle2, tone: 'text-emerald-700 bg-emerald-50' },
    { label: 'Declined today', value: overview.rejected_today, icon: XCircle, tone: 'text-red-700 bg-red-50' },
    { label: 'Active / governed models', value: `${overview.active_models} / ${overview.governed_models}`, icon: FileCheck2, tone: 'text-sky-700 bg-sky-50' },
  ] : [];
  return <div className="space-y-6"><div><p className="eyebrow">GlassBox / Admin</p><h1 className="mt-1 text-3xl font-bold text-[#102a4c]">Admin overview</h1><p className="mt-2 text-slate-500">Monitor decisions, governance, and operational risk from one workspace.</p></div>{error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}<div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{cards.map(({ label, value, icon: Icon, tone }) => <div key={label} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex items-center justify-between"><p className="text-sm text-slate-500">{label}</p><span className={`rounded-lg p-2 ${tone}`}><Icon size={18} /></span></div><p className="mt-5 text-2xl font-bold text-slate-800">{value}</p><p className="mt-1 text-xs text-slate-400">Live from the decision database</p></div>)}</div><section className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><div><p className="text-sm text-slate-500">Governance gate</p><p className={`mt-1 text-xl font-semibold ${overview?.governance_passed ? 'text-emerald-700' : 'text-red-700'}`}>{overview ? overview.governance_passed ? 'PASS' : 'FAIL' : 'Loading...'}</p><p className="mt-1 text-sm text-slate-500">Based on the latest persisted model governance checks.</p></div><Link to="/admin/review" className="rounded-md bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-800">Open review queue</Link></section></div>;
}
