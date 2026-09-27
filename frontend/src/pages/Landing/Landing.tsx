import { Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { BarChart3, CheckCircle2, ClipboardList, FilePlus2, XCircle } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { analyticsApi, type DashboardStats } from '../../services/api';
import { formatINR } from '../../utils/featureConfig';
import { StatusBadge } from '../../components/common/StatusBadge';

export default function Landing() {
  const { user } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  useEffect(() => { if (user) analyticsApi.dashboard().then(setStats).catch(() => setStats(null)); }, [user]);

  if (user) return <div className="space-y-6"><div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><p className="text-sm font-medium text-sky-700">Dashboard</p><h1 className="mt-1 text-3xl font-bold tracking-tight text-brand-900">Good morning, {user.full_name.split(' ')[0]}</h1><p className="mt-1 text-slate-500">Here’s an overview of your loan applications and credit risk activity.</p></div><Link to="/apply" className="inline-flex items-center justify-center gap-2 rounded-lg bg-brand-700 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-brand-800"><FilePlus2 size={17} />New application</Link></div><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{[{ label: 'Total Applications', value: stats?.total ?? 0, icon: ClipboardList, tone: 'text-sky-700 bg-sky-50' }, { label: 'Approved', value: stats?.approved ?? 0, icon: CheckCircle2, tone: 'text-emerald-700 bg-emerald-50' }, { label: 'Rejected', value: stats?.rejected ?? 0, icon: XCircle, tone: 'text-red-700 bg-red-50' }, { label: 'Approval Rate', value: stats?.approval_rate === null || stats?.approval_rate === undefined ? '—' : `${stats.approval_rate}%`, icon: BarChart3, tone: 'text-violet-700 bg-violet-50' }].map(({ label, value, icon: Icon, tone }) => <div key={label} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex justify-between"><p className="text-sm text-slate-500">{label}</p><span className={`rounded-lg p-2 ${tone}`}><Icon size={18} /></span></div><p className="mt-5 text-2xl font-bold text-slate-800">{value}</p><p className="mt-1 text-xs text-slate-400">Based on your recorded applications</p></div>)}</div><div className="grid gap-6 lg:grid-cols-3"><section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm lg:col-span-2"><div className="flex items-center justify-between"><div><h2 className="font-semibold text-slate-800">Recent Applications</h2><p className="text-sm text-slate-500">Latest AI credit assessments</p></div><Link to="/history" className="text-sm font-medium text-sky-700 hover:underline">View all</Link></div>{stats?.recent_applications.length ? <div className="mt-5 overflow-x-auto"><table className="w-full text-sm"><thead className="border-b text-left text-xs uppercase tracking-wide text-slate-400"><tr><th className="pb-3">Application</th><th className="pb-3">Loan amount</th><th className="pb-3">Decision</th><th className="pb-3">Risk</th></tr></thead><tbody>{stats.recent_applications.map(a => <tr key={a.id} className="border-b border-slate-100 last:border-0"><td className="py-3 font-medium text-slate-700">{a.application_id}</td><td className="py-3 text-slate-600">{formatINR(a.features.credit_amount)}</td><td className="py-3"><StatusBadge value={a.prediction?.decision ?? 'Under Review'} /></td><td className="py-3">{a.prediction && <StatusBadge value={a.prediction.risk_level} />}</td></tr>)}</tbody></table></div> : <div className="mt-5 rounded-lg bg-slate-50 p-8 text-center text-sm text-slate-500">No applications yet. Start a new assessment to see your activity here.</div>}</section><section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="font-semibold text-slate-800">Risk Distribution</h2><p className="text-sm text-slate-500">AI-derived risk levels</p><div className="mt-6 space-y-4">{[['Low risk', stats?.risk_distribution.low ?? 0, 'bg-emerald-500'], ['Medium risk', stats?.risk_distribution.medium ?? 0, 'bg-amber-500'], ['High risk', stats?.risk_distribution.high ?? 0, 'bg-red-500']].map(([label, value, color]) => <div key={String(label)}><div className="flex justify-between text-sm"><span className="text-slate-600">{label}</span><span className="font-semibold text-slate-800">{value}</span></div><div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100"><div className={`h-full ${color}`} style={{ width: `${stats?.total ? Number(value) / stats.total * 100 : 0}%` }} /></div></div>)}</div><p className="mt-7 rounded-lg bg-sky-50 p-3 text-xs leading-relaxed text-sky-800">Risk is an AI model indicator, not an official credit score or a bank decision.</p></section></div></div>;

  return (
    <div className="max-w-3xl mx-auto text-center py-12">
      <h1 className="text-3xl md:text-4xl font-bold text-brand-900">
        Loan decisions you can actually understand
      </h1>
      <p className="mt-4 text-slate-600">
        This system doesn't just say APPROVED or REJECTED. It explains what drove
        the decision using SHAP and LIME, shows what could change the outcome with
        counterfactual analysis, and audits its own predictions for fairness across groups.
      </p>
      <div className="mt-8 flex justify-center gap-4">
        <Link
          to={user ? '/apply' : '/register'}
          className="bg-brand-600 text-white px-5 py-2.5 rounded-md hover:bg-brand-700"
        >
          {user ? 'Start an Application' : 'Get Started'}
        </Link>
        {!user && (
          <Link to="/login" className="px-5 py-2.5 rounded-md border border-slate-300 hover:bg-slate-100">
            Log In
          </Link>
        )}
      </div>

      <div className="mt-16 grid sm:grid-cols-3 gap-6 text-left">
        <div className="rounded-lg border border-slate-200 bg-white p-5">
          <h3 className="font-semibold text-slate-800">Explainable</h3>
          <p className="mt-1 text-sm text-slate-500">
            Every decision comes with a SHAP and LIME breakdown of which factors mattered, and why.
          </p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-5">
          <h3 className="font-semibold text-slate-800">Actionable</h3>
          <p className="mt-1 text-sm text-slate-500">
            Counterfactual analysis shows what could realistically change your outcome.
          </p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-5">
          <h3 className="font-semibold text-slate-800">Audited</h3>
          <p className="mt-1 text-sm text-slate-500">
            A fairness dashboard tracks whether outcomes differ meaningfully across groups.
          </p>
        </div>
      </div>
    </div>
  );
}
