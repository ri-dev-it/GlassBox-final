import { useEffect, useMemo, useState } from 'react';
import { Activity, CheckCircle2, Clock3, FileText, TrendingUp, XCircle } from 'lucide-react';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { analyticsApi, type DashboardStats } from '../../services/api';
import RiskGradientBar from '../../components/common/RiskGradientBar';

export default function CreditAnalytics() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { analyticsApi.dashboard().then(setStats).catch((requestError) => setError(requestError?.response?.data?.error ?? 'Could not load credit analytics.')); }, []);

  const recent = stats?.recent_applications ?? [];
  const trend = useMemo(() => (stats?.recent_applications ?? []).slice().reverse().map((application) => ({ date: new Date(application.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }), score: application.prediction?.risk_score ?? 0 })), [stats]);
  const averageRisk = recent.length ? recent.reduce((sum, application) => sum + (application.prediction?.risk_score ?? 0), 0) / recent.length : 0;

  if (error) return <p className="text-sm text-red-700">{error}</p>;
  if (!stats) return <p className="text-sm text-slate-500">Loading credit analytics...</p>;
  if (!stats.total) return <div className="rounded-xl border border-dashed border-slate-300 p-10 text-center"><Activity className="mx-auto text-slate-400" /><h1 className="mt-3 text-xl font-semibold text-slate-800">No credit activity yet</h1><p className="mt-1 text-sm text-slate-500">Analytics will populate after the first application is recorded.</p></div>;

  return <div className="space-y-6">
    <div><p className="eyebrow">Portfolio pulse</p><h1 className="mt-1 text-3xl font-bold text-slate-900">Credit Analytics</h1><p className="mt-2 text-sm text-slate-500">Recorded application activity and model outcomes at a glance.</p></div>
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_18rem]">
      <div className="space-y-6">
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"><div className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-sm text-slate-500">Approval rate</p><p className="mt-2 text-5xl font-bold tracking-tight text-slate-900">{stats.approval_rate === null ? '—' : `${stats.approval_rate}%`}</p></div><span className="inline-flex items-center gap-1 rounded-full bg-lime-100 px-3 py-1 text-xs font-semibold text-lime-900"><TrendingUp size={14} /> recorded outcomes</span></div><div className="mt-7 h-64"><ResponsiveContainer width="100%" height="100%"><AreaChart data={trend}><defs><linearGradient id="riskTrend" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--accent)" stopOpacity={0.42} /><stop offset="100%" stopColor="var(--accent)" stopOpacity={0.02} /></linearGradient></defs><CartesianGrid strokeDasharray="3 3" stroke="var(--line)" /><XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="var(--muted)" /><YAxis domain={[0, 100]} tick={{ fontSize: 11 }} stroke="var(--muted)" /><Tooltip /><Area type="monotone" dataKey="score" name="Risk score" stroke="var(--accent)" fill="url(#riskTrend)" strokeWidth={3} /></AreaChart></ResponsiveContainer></div><p className="mt-2 text-xs text-slate-500">Risk score trend across the latest recorded applications.</p></section>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><Stat icon={CheckCircle2} label="Approved" value={stats.approved} /><Stat icon={XCircle} label="Declined" value={stats.rejected} /><Stat icon={Clock3} label="Under review" value={stats.under_review} /><Stat icon={FileText} label="Total records" value={stats.total} /></div>
      </div>
      <aside className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><p className="text-sm font-semibold text-slate-800">Aggregate risk</p><p className="mt-1 text-xs text-slate-500">Average score from the latest recorded assessments.</p><p className="mt-4 text-3xl font-bold text-slate-900">{Math.round(averageRisk)}<span className="text-base font-medium text-slate-500"> / 100</span></p><div className="mt-5"><RiskGradientBar value={averageRisk} label="Average application risk" /></div><div className="mt-7 space-y-3"><p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Recent activity</p>{recent.map((application) => <div key={application.id} className="flex items-center gap-3 rounded-lg bg-slate-50 p-3"><span className="rounded-full bg-lime-100 p-2 text-lime-900"><Activity size={15} /></span><div className="min-w-0 flex-1"><p className="truncate text-sm font-medium text-slate-800">{application.application_id}</p><p className="text-xs text-slate-500">{application.prediction?.decision ?? 'Processing'}</p></div><span className="text-xs font-semibold text-slate-600">{application.prediction?.risk_score ?? '—'}</span></div>)}</div></aside>
    </div>
  </div>;
}

function Stat({ icon: Icon, label, value }: { icon: typeof CheckCircle2; label: string; value: number }) {
  return <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"><Icon size={17} className="text-brand-700" /><p className="mt-4 text-xs text-slate-500">{label}</p><p className="mt-1 text-2xl font-bold text-slate-900">{value}</p></div>;
}
