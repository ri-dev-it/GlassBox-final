import { useEffect, useState } from 'react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { portfolioApi } from '../../services/api';
import type { PortfolioExposure } from '../../types';
import RiskGradientBar from '../../components/common/RiskGradientBar';

export default function Portfolio() {
  const [portfolio, setPortfolio] = useState<PortfolioExposure | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    portfolioApi.exposure().then(setPortfolio).catch((requestError) => setError(requestError?.response?.data?.error ?? 'Could not load portfolio exposure.'));
  }, []);

  if (error) return <p className="text-red-700">{error}</p>;
  if (!portfolio) return <p className="text-slate-500">Loading portfolio...</p>;

  const totalMerchants = portfolio.tier_summary.reduce((sum, tier) => sum + tier.merchant_count, 0);
  const topTierMerchants = portfolio.tier_summary[portfolio.tier_summary.length - 1]?.merchant_count ?? 0;
  const portfolioPosition = totalMerchants ? (topTierMerchants / totalMerchants) * 100 : 0;

  return <div className="max-w-5xl space-y-6">
    <div><p className="text-sm font-medium text-sky-700">Simulated merchant portfolio</p><h1 className="mt-1 text-3xl font-bold text-[#102a4c]">Portfolio Overview</h1><p className="mt-2 text-sm text-slate-500">Tier counts and estimated exposure use synthetic merchants, illustrative thresholds, and demo exposure amounts. They are not real Razorpay Capital policy.</p></div>
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{portfolio.tier_summary.map((tier) => <article key={tier.tier} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"><p className="text-sm font-semibold text-slate-700">{tier.tier}</p><p className="mt-3 text-2xl font-bold text-brand-900">{tier.merchant_count}</p><p className="text-xs text-slate-500">merchants</p><p className="mt-3 text-sm text-slate-600">Estimated exposure: <strong>₹{tier.estimated_exposure.toLocaleString()}</strong></p></article>)}</div>
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex flex-wrap items-start justify-between gap-5"><div><h2 className="text-lg font-semibold text-slate-800">Portfolio risk spectrum</h2><p className="mt-1 text-xs text-slate-500">Position reflects the share of merchants in the highest illustrative tier.</p></div><strong className="text-2xl text-slate-900">{Math.round(portfolioPosition)}%</strong></div><div className="mt-6"><RiskGradientBar value={portfolioPosition} /></div></section>
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="text-lg font-semibold text-slate-800">Common blockers to tier advancement</h2><p className="mt-1 text-xs text-slate-500">Count of merchants whose next illustrative tier is blocked by each signal.</p><div className="mt-4 h-80"><ResponsiveContainer width="100%" height="100%"><BarChart data={portfolio.blocking_signals} layout="vertical" margin={{ left: 40, right: 20 }}><CartesianGrid strokeDasharray="3 3" /><XAxis type="number" /><YAxis type="category" dataKey="feature" width={180} tick={{ fontSize: 11 }} /><Tooltip /><Bar dataKey="merchant_count" fill="var(--accent)" /></BarChart></ResponsiveContainer></div></section>
    <p className="text-xs text-slate-500">{portfolio.disclaimer}</p>
  </div>;
}
