import { useEffect, useState } from 'react';
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';
import { BarChart3, ShieldAlert } from 'lucide-react';
import { analyticsApi, type DashboardStats } from '../../services/api';

const riskColours = ['var(--approved)', 'var(--review)', 'var(--rejected)'];
const decisionColours = ['var(--approved)', 'var(--review)', 'var(--rejected)'];

export default function RiskAnalysis() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    analyticsApi.dashboard().then(setStats).catch((requestError) => setError(requestError?.response?.data?.error ?? 'Could not load risk analysis.'));
  }, []);

  if (error) return <p className="text-sm text-red-700">{error}</p>;
  if (!stats) return <p className="text-sm text-slate-500">Loading risk analysis...</p>;
  if (!stats.total) return <div className="rounded-xl border border-dashed border-slate-300 p-10 text-center"><ShieldAlert className="mx-auto text-slate-400" /><h1 className="mt-3 text-xl font-semibold text-slate-800">No risk data yet</h1><p className="mt-1 text-sm text-slate-500">Risk charts will appear after the first application is recorded.</p></div>;

  const riskData = [{ name: 'Low', value: stats.risk_distribution.low }, { name: 'Medium', value: stats.risk_distribution.medium }, { name: 'High', value: stats.risk_distribution.high }];
  const decisionData = [{ name: 'Approve', value: stats.approved }, { name: 'Review', value: stats.under_review }, { name: 'Decline', value: stats.rejected }];

  return <div className="space-y-6">
    <div><p className="eyebrow">Decision intelligence</p><h1 className="mt-1 text-3xl font-bold text-slate-900">Risk Analysis</h1><p className="mt-2 text-sm text-slate-500">A live view of recorded application outcomes and model risk levels.</p></div>
    <div className="grid gap-4 sm:grid-cols-3"><Metric label="Applications" value={stats.total} /><Metric label="Approval rate" value={stats.approval_rate === null ? '—' : `${stats.approval_rate}%`} /><Metric label="Under review" value={stats.under_review} /></div>
    <div className="grid gap-6 lg:grid-cols-2">
      <ChartCard title="Risk level distribution" icon={ShieldAlert} data={riskData} colours={riskColours} />
      <ChartCard title="Decision breakdown" icon={BarChart3} data={decisionData} colours={decisionColours} />
    </div>
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex items-center gap-2"><ShieldAlert size={18} className="text-brand-700" /><h2 className="font-semibold text-slate-800">Fraud flag summary</h2></div>{stats.fraud_flag_summary.length === 0 ? <p className="mt-3 text-sm text-slate-500">No persisted merchant fraud flags are available yet.</p> : <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{stats.fraud_flag_summary.map(({ flag, count }) => <div key={flag} className="rounded-lg bg-slate-50 p-3"><p className="text-sm text-slate-600">{flag}</p><p className="mt-1 text-xl font-semibold text-slate-800">{count}</p></div>)}</div>}</section>
  </div>;
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><p className="text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</p><p className="mt-3 text-3xl font-bold text-slate-900">{value}</p></div>;
}

function ChartCard({ title, icon: Icon, data, colours }: { title: string; icon: typeof ShieldAlert; data: Array<{ name: string; value: number }>; colours: string[] }) {
  return <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex items-center gap-2"><Icon size={18} className="text-brand-700" /><h2 className="font-semibold text-slate-800">{title}</h2></div><div className="mt-3 h-64"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={58} outerRadius={88} paddingAngle={data.length > 1 ? 3 : 0} label={({ name, value }) => `${name}: ${value}`}>{data.map((entry, index) => <Cell key={entry.name} fill={colours[index]} />)}</Pie><Tooltip /></PieChart></ResponsiveContainer></div></section>;
}
