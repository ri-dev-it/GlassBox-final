import type { VerificationReport } from '../../types';

export default function VerificationReportView({ report }: { report: VerificationReport }) {
  return <section className="mt-5 rounded-xl border border-slate-200 bg-white p-5">
    <h2 className="text-lg font-semibold">Document verification: {report.verdict.replaceAll('_', ' ')}</h2>
    {report.identity.aadhaar && <p className="mt-2 text-sm">Aadhaar: {report.identity.aadhaar}</p>}
    <p className="mt-2 text-xs text-slate-500">Heuristic consistency checks; not government or bank authentication.</p>
    <div className="mt-4 overflow-x-auto"><table className="w-full text-left text-sm">
      <thead><tr><th className="p-2">Document / check</th><th className="p-2">Status</th><th className="p-2">Reason</th></tr></thead>
      <tbody>{report.checks.map((check, index) => <tr key={`${check.slot}-${check.name}-${index}`} className="border-t">
        <td className="p-2">{check.slot?.replaceAll('_', ' ')} / {check.name.replaceAll('_', ' ')}</td>
        <td className={`p-2 font-semibold ${check.status === 'PASS' ? 'text-green-700' : check.status === 'FAIL' ? 'text-red-700' : 'text-amber-700'}`}>{check.status}</td>
        <td className="p-2">{check.reason}</td>
      </tr>)}</tbody>
    </table></div>
    {Object.keys(report.features).length > 0 && <details className="mt-4"><summary>Bank transaction features</summary>
      <dl className="mt-2 grid gap-2 sm:grid-cols-2">{Object.entries(report.features).map(([key, value]) => <div key={key}>
        <dt className="text-xs text-slate-500">{key.replaceAll('_', ' ')}</dt><dd>{value ?? 'Not available'}</dd>
      </div>)}</dl></details>}
  </section>;
}
