import type { VerificationReport } from '../../types';
import BankStatementDetails from './BankStatementDetails';

export default function VerificationReportView({ report, showBankStatement = true }: { report: VerificationReport; showBankStatement?: boolean }) {
  return <section className="mt-5 rounded-xl border border-slate-200 bg-white p-5">
    <h2 className="text-lg font-semibold">Document verification: {report.verdict.replaceAll('_', ' ')}</h2>
    {report.historicalPolicy && <p className="mt-2 text-xs text-slate-500">This recorded verdict used an earlier document policy. The submitted decision is unchanged.</p>}
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
    {showBankStatement && report.bankStatement && <BankStatementDetails statement={report.bankStatement} />}
  </section>;
}
