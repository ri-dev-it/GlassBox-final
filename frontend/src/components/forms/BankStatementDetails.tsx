import type { BankStatementDetail } from '../../types';

const STATS: Array<[string, string, 'money' | 'percent' | 'number']> = [
  ['avg_monthly_credits', 'Average monthly credits', 'money'],
  ['salary_regularity', 'Salary regularity (months)', 'number'],
  ['avg_monthly_balance', 'Average monthly balance', 'money'],
  ['min_monthly_balance', 'Minimum balance', 'money'],
  ['emi_debit_count', 'EMI / loan debit count', 'number'],
  ['emi_debit_share', 'EMI / loan debit share', 'percent'],
  ['fixed_obligation_to_income_ratio', 'Fixed obligations / income', 'percent'],
  ['bounced_payment_count', 'Bounced / returned payments', 'number'],
  ['cash_withdrawal_share', 'Cash withdrawal share', 'percent'],
  ['negative_balance_days', 'Overdraft / negative balance days', 'number'],
  ['transaction_velocity', 'Transactions per day', 'number'],
  ['income_volatility', 'Income volatility', 'number'],
];
const money = (value: number) => value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export default function BankStatementDetails({ statement }: { statement: BankStatementDetail }) {
  return <section className="mt-5 rounded-xl border border-slate-200 bg-white p-4">
    <h3 className="font-semibold text-slate-800">Parsed bank statement</h3>
    {statement.accountHolder ? <p className="mt-2 text-sm">Account holder: <strong>{statement.accountHolder}</strong></p>
      : <p className="mt-2 text-sm text-amber-800">Account holder name could not be extracted — manual review required</p>}
    {statement.period && <p className="mt-2 text-sm text-slate-600">Decision window: {statement.period.start} to {statement.period.end} ({statement.period.transaction_count} transactions)</p>}
    <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
      <div><dt className="text-slate-500">Account number</dt><dd>{statement.accountNumber ?? 'Could not be extracted'}</dd></div>
      <div><dt className="text-slate-500">Bank</dt><dd>{statement.bankName ?? 'Not available'}</dd></div>
      <div><dt className="text-slate-500">Branch</dt><dd>{statement.branch ?? 'Not available'}</dd></div>
      <div><dt className="text-slate-500">IFSC</dt><dd>{statement.ifsc ?? 'Not available'}</dd></div>
    </dl>
    {statement.transactions.length ? <div className="mt-4 max-h-96 overflow-auto"><table className="w-full text-left text-sm">
      <caption className="sr-only">Extracted bank transactions</caption>
      <thead className="sticky top-0 bg-slate-50"><tr>{['Date', 'Description', 'Debit', 'Credit', 'Balance'].map(label => <th scope="col" key={label} className="p-2">{label}</th>)}</tr></thead>
      <tbody>{statement.transactions.map((row, i) => <tr key={i} className="border-t">
        <td className="whitespace-nowrap p-2">{row.date}</td><td className="min-w-40 p-2">{row.description}</td>
        <td className="p-2 tabular-nums">{money(row.debit)}</td><td className="p-2 tabular-nums">{money(row.credit)}</td><td className="p-2 tabular-nums">{money(row.balance)}</td>
      </tr>)}</tbody>
    </table></div> : <p className="mt-4 text-sm text-slate-600">No transactions could be extracted from this statement</p>}
    <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{STATS.map(([key, label, format]) => {
      const value = statement.features[key];
      return <div key={key} className="rounded-lg border border-slate-200 bg-slate-50 p-3"><p className="text-xs text-slate-500">{label}</p>
        <p className="mt-1 font-semibold">{value == null ? 'Not available' : format === 'money' ? `₹${money(value)}` : format === 'percent' ? `${(value * 100).toFixed(1)}%` : value.toLocaleString('en-IN', { maximumFractionDigits: 3 })}</p></div>;
    })}</div>
    <p className="mt-3 text-xs text-slate-500">Transactions and features are limited to the latest 90 days available in the statement. Descriptions and recurring income are interpreted heuristically.</p>
  </section>;
}
