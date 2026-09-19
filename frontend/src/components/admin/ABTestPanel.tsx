import { useEffect, useState } from 'react';
import type { ABTest, ABTestResults, ModelVersion } from '../../types';
import { analyticsApi } from '../../services/api';

const MODEL_NAME = 'credit_history';

export default function ABTestPanel() {
  const [versions, setVersions] = useState<ModelVersion[]>([]);
  const [tests, setTests] = useState<ABTest[]>([]);
  const [selectedTest, setSelectedTest] = useState<ABTestResults | null>(null);
  const [control, setControl] = useState('');
  const [treatment, setTreatment] = useState('');
  const [traffic, setTraffic] = useState('50');
  const [message, setMessage] = useState<string | null>(null);

  const refresh = () => {
    analyticsApi.modelVersions(MODEL_NAME).then((items) => {
      setVersions(items.filter((version) => version.governance_passed));
      if (items.length > 1) {
        setControl(String(items[0].id));
        setTreatment(String(items[1].id));
      }
    }).catch(() => setMessage('Could not load model versions.'));
    analyticsApi.abTests(MODEL_NAME).then(setTests).catch(() => setMessage('Could not load A/B tests.'));
  };

  useEffect(refresh, []);

  const loadResults = (test: ABTest) => {
    setSelectedTest(null);
    analyticsApi.abTestResults(MODEL_NAME, test.id).then(setSelectedTest).catch(() => setMessage('Could not load test results.'));
  };

  const start = () => {
    setMessage(null);
    analyticsApi.startABTest(MODEL_NAME, {
      control_version_id: Number(control), treatment_version_id: Number(treatment), traffic_percentage: Number(traffic),
    }).then(() => { setMessage('A/B test started.'); refresh(); }).catch((error) => setMessage(error?.response?.data?.error ?? 'Could not start A/B test.'));
  };

  const end = (test: ABTest) => {
    analyticsApi.endABTest(MODEL_NAME, test.id).then(() => { setMessage('A/B test ended.'); refresh(); }).catch((error) => setMessage(error?.response?.data?.error ?? 'Could not end A/B test.'));
  };

  const activate = (version: ModelVersion) => {
    analyticsApi.activateModelVersion(MODEL_NAME, version.id).then(() => { setMessage(`Version ${version.version_number} activated.`); refresh(); }).catch((error) => setMessage(error?.response?.data?.error ?? 'Could not activate version.'));
  };

  return <div className="space-y-4">
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="font-medium text-slate-800">Model version history</h2>
      <div className="mt-3 overflow-x-auto"><table className="w-full min-w-[620px] text-sm"><thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2">Version</th><th className="pb-2">Trained</th><th className="pb-2">F1</th><th className="pb-2">Governance</th><th className="pb-2">Status</th><th className="pb-2" /></tr></thead><tbody>{versions.map((version) => <tr key={version.id} className="border-b border-slate-100 last:border-0"><td className="py-2 font-medium">v{version.version_number}</td><td className="py-2 text-slate-600">{version.trained_at ? new Date(version.trained_at).toLocaleString() : '—'}</td><td className="py-2 text-slate-600">{version.metrics.f1 == null ? '—' : Number(version.metrics.f1).toFixed(3)}</td><td className="py-2"><span className={version.governance_passed ? 'text-green-700' : 'text-red-700'}>{version.governance_passed ? 'Passed' : 'Rejected'}</span></td><td className="py-2">{version.is_active ? <span className="font-semibold text-brand-700">Active</span> : 'Inactive'}</td><td className="py-2 text-right">{version.governance_passed && !version.is_active && <button type="button" onClick={() => activate(version)} className="text-brand-700 hover:underline">Activate</button>}</td></tr>)}</tbody></table></div>
    </div>
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="font-medium text-slate-800">Model A/B testing</h2>
      <p className="mt-1 text-xs text-slate-500">Route new credit applications between governed model versions and compare recorded outcomes.</p>
      <div className="mt-4 grid gap-3 sm:grid-cols-4">
        <label className="text-xs text-slate-600">Control version<select value={control} onChange={(event) => setControl(event.target.value)} className="mt-1 w-full rounded border border-slate-300 p-2 text-sm"><option value="">Select version</option>{versions.map((version) => <option key={version.id} value={version.id}>v{version.version_number} (#{version.id})</option>)}</select></label>
        <label className="text-xs text-slate-600">Treatment version<select value={treatment} onChange={(event) => setTreatment(event.target.value)} className="mt-1 w-full rounded border border-slate-300 p-2 text-sm"><option value="">Select version</option>{versions.map((version) => <option key={version.id} value={version.id}>v{version.version_number} (#{version.id})</option>)}</select></label>
        <label className="text-xs text-slate-600">Treatment traffic (%)<input type="number" min="0" max="100" value={traffic} onChange={(event) => setTraffic(event.target.value)} className="mt-1 w-full rounded border border-slate-300 p-2 text-sm" /></label>
        <button type="button" onClick={start} disabled={!control || !treatment || control === treatment} className="self-end rounded bg-brand-700 px-3 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50">Start test</button>
      </div>
      {message && <p className="mt-3 text-sm text-amber-700">{message}</p>}
    </div>
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="font-medium text-slate-800">Test history</h2>
      {!tests.length && <p className="mt-2 text-sm text-slate-500">No A/B tests have been started.</p>}
      <div className="mt-3 space-y-2">{tests.map((test) => <div key={test.id} className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-2 text-sm last:border-0"><div><span className="font-medium text-slate-700">{test.name}</span><span className="ml-2 text-xs text-slate-500">{test.status} · {test.traffic_percentage}% treatment</span></div><div className="flex gap-2"><button type="button" onClick={() => loadResults(test)} className="text-brand-700 hover:underline">View results</button>{test.status === 'active' && <button type="button" onClick={() => end(test)} className="text-red-700 hover:underline">End test</button>}</div></div>)}</div>
    </div>
    {selectedTest && <div className="rounded-lg border border-slate-200 bg-white p-4"><h2 className="font-medium text-slate-800">{selectedTest.test.name} results</h2><div className="mt-3 grid gap-3 sm:grid-cols-2">{(['control', 'treatment'] as const).map((variant) => { const summary = selectedTest.summary[variant]; return <div key={variant} className="rounded bg-slate-50 p-3 text-sm"><p className="font-medium capitalize text-slate-700">{variant}</p><p className="mt-1 text-slate-600">{summary.count} routed · {summary.approval_rate === null ? 'No outcomes' : `${(summary.approval_rate * 100).toFixed(1)}% approved`}</p><p className="text-xs text-slate-500">Average approval probability: {summary.average_probability === null ? '—' : `${(summary.average_probability * 100).toFixed(1)}%`}</p></div>; })}</div></div>}
  </div>;
}