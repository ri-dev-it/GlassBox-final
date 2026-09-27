import { useEffect, useMemo, useState } from 'react';
import { isAxiosError } from 'axios';
import { adminApi, type AdminReviewApplication } from '../../services/api';
import { StatusBadge } from '../../components/common/StatusBadge';

export default function ReviewQueue() {
  const [reviews, setReviews] = useState<AdminReviewApplication[]>([]);
  const [expandedApplicant, setExpandedApplicant] = useState<number | null>(null);
  const [expandedApplication, setExpandedApplication] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<number | null>(null);
  useEffect(() => { adminApi.pendingReviews().then(setReviews).catch((requestError) => setError(requestError?.response?.data?.error ?? 'Could not load the review queue.')); }, []);
  const groups = useMemo(() => Object.values(reviews.reduce<Record<number, { applicantId: number; name: string; email: string; applications: AdminReviewApplication[] }>>((all, review) => {
    const key = review.applicant_id;
    (all[key] ??= { applicantId: key, name: review.applicant.full_name, email: review.applicant.email, applications: [] }).applications.push(review);
    return all;
  }, {})), [reviews]);
  const decide = async (id: number, decision: 'APPROVE' | 'REJECT') => {
    setBusy(id); setError(null);
    try { await adminApi.decideReview(id, decision); setReviews((items) => items.filter((item) => item.id !== id)); setExpandedApplication(null); }
    catch (requestError) { setError(isAxiosError(requestError) ? requestError.response?.data?.error ?? 'Could not save the decision.' : 'Could not save the decision.'); }
    finally { setBusy(null); }
  };
  const actions = (review: AdminReviewApplication) => <div className="flex gap-2"><button type="button" disabled={busy === review.id} onClick={() => decide(review.id, 'APPROVE')} className="rounded-md bg-green-700 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">Approve</button><button type="button" disabled={busy === review.id} onClick={() => decide(review.id, 'REJECT')} className="rounded-md bg-red-700 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">Reject</button></div>;
  const explanation = (review: AdminReviewApplication) => <><button type="button" onClick={() => setExpandedApplication(expandedApplication === review.id ? null : review.id)} className="mt-4 text-sm font-medium text-brand-700 hover:underline">{expandedApplication === review.id ? 'Hide explanation' : 'View SHAP, LIME and counterfactual'}</button>{expandedApplication === review.id && <div className="mt-4 grid gap-4 border-t border-slate-100 pt-4 md:grid-cols-3"><div><h3 className="text-sm font-semibold text-slate-700">SHAP</h3><p className="mt-1 text-sm text-slate-600">{review.shap?.plain_english ?? 'No stored SHAP explanation.'}</p></div><div><h3 className="text-sm font-semibold text-slate-700">LIME</h3><p className="mt-1 text-sm text-slate-600">{review.lime?.plain_english ?? 'No stored LIME explanation.'}</p></div><div><h3 className="text-sm font-semibold text-slate-700">DiCE counterfactual</h3><p className="mt-1 text-sm text-slate-600">{review.counterfactual?.message ?? 'No counterfactual was generated.'}</p></div></div>}</>;
  return <div className="space-y-6"><div><p className="eyebrow">Admin / Review Queue</p><h1 className="mt-1 text-3xl font-bold text-brand-900">Manual review queue</h1><p className="mt-2 text-slate-500">Every item below is a model REVIEW decision awaiting an auditable final decision.</p></div>{error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}{groups.length === 0 ? <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">No applications are awaiting review.</div> : <div className="space-y-3">{groups.map(group => {
    const single = group.applications.length === 1; const isOpen = expandedApplicant === group.applicantId;
    return <article key={group.applicantId} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex flex-wrap items-center justify-between gap-4"><button type="button" onClick={() => setExpandedApplicant(isOpen ? null : group.applicantId)} className="text-left"><h2 className="text-lg font-semibold text-slate-800">{group.name}{group.applications.length > 1 && <span className="ml-2 rounded-full bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-600">{group.applications.length} applications</span>}</h2><p className="text-sm text-slate-500">{group.email}</p></button>{single && actions(group.applications[0])}</div>
      {single ? <div className="mt-3 flex flex-wrap items-center gap-2 text-xs"><span className="font-semibold uppercase tracking-wide text-slate-400">{group.applications[0].application_id}</span><span className="rounded-full bg-amber-50 px-2 py-1 font-semibold text-amber-800">REVIEW</span><span className="rounded-full bg-slate-100 px-2 py-1 text-slate-600">Risk score {group.applications[0].prediction?.risk_score ?? '—'} / 100</span><StatusBadge value={group.applications[0].prediction?.risk_level ?? 'MEDIUM'} /></div> : null}
      {!single && isOpen && <div className="mt-4 space-y-3 border-t border-slate-100 pt-4">{group.applications.map(review => <div key={review.id} className="rounded-lg border border-slate-200 p-4"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{review.application_id}</p><div className="mt-2 flex flex-wrap gap-2 text-xs"><span className="rounded-full bg-amber-50 px-2 py-1 font-semibold text-amber-800">REVIEW</span><span className="rounded-full bg-slate-100 px-2 py-1 text-slate-600">Risk score {review.prediction?.risk_score ?? '—'} / 100</span><StatusBadge value={review.prediction?.risk_level ?? 'MEDIUM'} /></div></div>{actions(review)}</div>{explanation(review)}</div>)}</div>}
      {single && explanation(group.applications[0])}</article>;
  })}</div>}</div>;
}
