import { useEffect, useState } from 'react';
import { isAxiosError } from 'axios';
import type { ModelMetadata, ModelsMetrics, GlobalShapEntry, FairnessReport, ApplicationsSummary } from '../../types';
import { adminApi, analyticsApi, type AdminReviewApplication } from '../../services/api';
import StatCard from '../../components/dashboard/StatCard';
import GlobalImportanceChart from '../../components/charts/GlobalImportanceChart';
import FairnessGroupChart from '../../components/charts/FairnessGroupChart';
import ABTestPanel from '../../components/admin/ABTestPanel';

type Tab = 'overview' | 'explainability' | 'fairness' | 'ab_tests';

export default function Admin() {
  const [tab, setTab] = useState<Tab>('overview');
  const [summary, setSummary] = useState<ApplicationsSummary | null>(null);
  const [metadata, setMetadata] = useState<ModelMetadata | null>(null);
  const [modelMetrics, setModelMetrics] = useState<ModelsMetrics | null>(null);
  const [globalShap, setGlobalShap] = useState<GlobalShapEntry[] | null>(null);
  const [fairness, setFairness] = useState<FairnessReport | null>(null);
  const [pendingReviews, setPendingReviews] = useState<AdminReviewApplication[]>([]);
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    analyticsApi.applicationsSummary().then(setSummary).catch(() => undefined);
    analyticsApi.model().then(setMetadata).catch((e) => setError(e?.response?.data?.error ?? 'Model not trained yet.'));
    analyticsApi.models().then(setModelMetrics).catch(() => undefined);
    adminApi.pendingReviews().then(setPendingReviews).catch((e) => setReviewError(e?.response?.data?.error ?? 'Could not load pending reviews.'));
  }, []);

  const decideReview = async (applicationId: number, decision: 'APPROVE' | 'REJECT') => {
    try {
      await adminApi.decideReview(applicationId, decision);
      setPendingReviews((reviews) => reviews.filter((review) => review.id !== applicationId));
    } catch (error) {
      setReviewError(isAxiosError(error) ? error.response?.data?.error ?? 'Could not save the admin decision.' : 'Could not save the admin decision.');
    }
  };

  useEffect(() => {
    if (tab === 'explainability' && !globalShap) {
      analyticsApi.globalShap().then(setGlobalShap).catch(() => undefined);
    }
    if (tab === 'fairness' && !fairness) {
      analyticsApi.fairness().then(setFairness).catch(() => undefined);
    }
  }, [tab, globalShap, fairness]);

  return (
    <div>
      <h1 className="text-2xl font-semibold text-brand-900 mb-6">Admin Dashboard</h1>

      <div className="flex gap-4 border-b border-slate-200 mb-6 text-sm">
        {(['overview', 'explainability', 'fairness', 'ab_tests'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`pb-2 px-1 capitalize ${tab === t ? 'border-b-2 border-brand-600 text-brand-700 font-medium' : 'text-slate-500'}`}
          >
            {t}
          </button>
        ))}
      </div>

      {error && <p className="text-sm text-amber-600 mb-4">{error}</p>}
      {reviewError && <p role="alert" className="mb-4 text-sm text-red-700">{reviewError}</p>}

      {tab === 'overview' && (
        <div className="space-y-6">
          {summary && (
            <div className="grid sm:grid-cols-4 gap-4">
              <StatCard label="Total Applications" value={summary.total} />
              <StatCard label="Approved" value={summary.approved} tone="approved" />
              <StatCard label="Rejected" value={summary.rejected} tone="rejected" />
              <StatCard label="Approval Rate" value={summary.approval_rate !== null ? `${(summary.approval_rate * 100).toFixed(1)}%` : '—'} />
            </div>
          )}
          <section className="rounded-lg border border-amber-200 bg-white p-4">
            <div className="flex flex-wrap items-center justify-between gap-2"><div><h2 className="font-medium text-slate-800">Pending manual review</h2><p className="mt-1 text-xs text-slate-500">REVIEW-band applications require an auditable admin decision.</p></div><span className="rounded-full bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-800">{pendingReviews.length} pending</span></div>
            {pendingReviews.length === 0 ? <p className="mt-4 text-sm text-slate-500">No applications are awaiting review.</p> : <div className="mt-4 space-y-3">{pendingReviews.map((review) => <div key={review.id} className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-slate-200 p-3"><div><p className="font-medium text-slate-800">{review.application_id}</p><p className="text-sm text-slate-500">{review.applicant.full_name} · {review.applicant.email}</p><p className="text-xs text-slate-400">{new Date(review.created_at).toLocaleString()}</p></div><div className="flex gap-2"><button type="button" onClick={() => decideReview(review.id, 'APPROVE')} className="rounded-md bg-green-700 px-3 py-2 text-xs font-semibold text-white hover:bg-green-800">Approve</button><button type="button" onClick={() => decideReview(review.id, 'REJECT')} className="rounded-md bg-red-700 px-3 py-2 text-xs font-semibold text-white hover:bg-red-800">Reject</button></div></div>)}</div>}
          </section>
          {metadata && (
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <h2 className="font-medium text-slate-800 mb-3">Model Performance ({metadata.final_model})</h2>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
                {([
                  ['Precision', metadata.precision, 'Of applications we approved, what fraction were actually good loans'],
                  ['Recall', metadata.recall, 'Of actually good loans, what fraction did we approve'],
                  ['F1 Score', metadata.f1, 'A balance between precision and recall'],
                  ['ROC-AUC', metadata.roc_auc, 'How well the model separates good and risky loans'],
                ] as Array<[string, number, string]>).map(([label, value, description]) => (
                  <div key={label} title={description} className="rounded-md bg-slate-50 p-3">
                    <p className="text-xs font-medium text-slate-500">{label}</p>
                    <p className="mt-1 text-xl font-semibold text-brand-900">{Number(value).toFixed(3)}</p>
                  </div>
                ))}
              </div>
              <div className="grid sm:grid-cols-2 gap-4">
                {Object.entries(metadata.model_comparison).map(([name, m]) => (
                  <div key={name} className="text-sm">
                    <p className="font-medium text-slate-700">{name}</p>
                    <p className="text-slate-500">Accuracy: {m.accuracy.toFixed(3)} · Precision: {m.precision.toFixed(3)}</p>
                    <p className="text-slate-500">Recall: {m.recall.toFixed(3)} · F1: {m.f1.toFixed(3)}</p>
                    {m.roc_auc !== undefined && <p className="text-slate-500">ROC-AUC: {m.roc_auc.toFixed(3)}</p>}
                  </div>
                ))}
              </div>
              <p className="text-xs text-slate-400 mt-3">
                Trained on {metadata.dataset_size} records ({metadata.train_size} train / {metadata.test_size} test).
              </p>
            </div>
          )}
          {modelMetrics && (
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <h2 className="font-medium text-slate-800 mb-1">Model Metrics Comparison</h2>
              <p className="text-xs text-slate-500 mb-3">Held-out test-set metrics. Hover a column heading for a plain-English explanation.</p>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[620px] text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 text-left text-slate-500">
                      <th className="pb-2 font-medium">Model</th>
                      <th className="pb-2 font-medium" title="Of positive predictions, the fraction that were actually positive">Precision</th>
                      <th className="pb-2 font-medium" title="Of actual positive cases, the fraction the model found">Recall</th>
                      <th className="pb-2 font-medium" title="The balance between precision and recall">F1 Score</th>
                      <th className="pb-2 font-medium" title="How well the model separates the two classes">ROC-AUC</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(modelMetrics.latest).map(([key, metric]) => (
                      <tr key={key} className="border-b border-slate-100 last:border-0">
                        <td className="py-3 font-medium text-slate-700"><div>{key === 'income_model' ? 'Income-based model' : 'Transaction-based model'}</div><span className={`mt-1 inline-block rounded-full px-2 py-0.5 text-xs font-semibold ${metric.governance.passed ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>{metric.governance.passed ? 'Governance passed' : 'Governance failed'}</span></td>
                        <td className="py-3 text-slate-600">{metric.precision.toFixed(3)}</td>
                        <td className="py-3 text-slate-600">{metric.recall.toFixed(3)}</td>
                        <td className="py-3 text-slate-600">{metric.f1.toFixed(3)}</td>
                        <td className="py-3 text-slate-600">{metric.roc_auc.toFixed(3)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {tab === 'explainability' && (
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="font-medium text-slate-800 mb-1">Global Feature Importance</h2>
          <p className="text-xs text-slate-500 mb-3">What generally influences the model, averaged across sampled applicants.</p>
          {globalShap ? <GlobalImportanceChart data={globalShap} /> : <p className="text-slate-500 text-sm">Loading…</p>}
        </div>
      )}

      {tab === 'fairness' && (
        <div className="space-y-4">
          {fairness ? (
            <>
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
                {fairness.protected_attribute_caveat}
              </div>
              <div className="rounded-lg border border-slate-200 bg-white p-4">
                <h2 className="font-medium text-slate-800 mb-3">Group Comparison ({fairness.protected_attribute})</h2>
                <FairnessGroupChart groupMetrics={fairness.group_metrics} />
              </div>
              <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm space-y-1">
                <h2 className="font-medium text-slate-800 mb-2">Interpretation</h2>
                {fairness.interpretation.map((line, i) => <p key={i} className="text-slate-600">{line}</p>)}
                <p className="text-xs text-slate-400 mt-2">{fairness.disclaimer}</p>
              </div>
            </>
          ) : (
            <p className="text-slate-500 text-sm">Loading…</p>
          )}
        </div>
      )}

      {tab === 'ab_tests' && <ABTestPanel />}
    </div>
  );
}
