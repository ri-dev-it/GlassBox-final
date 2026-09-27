import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import type { ApplicationDetail } from '../../types';
import { applicationApi } from '../../services/api';
import { formatINR } from '../../utils/featureConfig';
import { StatusBadge } from '../../components/common/StatusBadge';

type Row = ApplicationDetail['application'] & { prediction: ApplicationDetail['prediction'] };

export default function History() {
  const [applications, setApplications] = useState<Row[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    applicationApi
      .list()
      .then((apps) => setApplications(apps as Row[]))
      .catch(() => setError('Could not load application history.'));
  }, []);

  return (
    <div><div className="mb-6"><p className="text-sm font-medium text-sky-700">Applications</p><h1 className="mt-1 text-3xl font-bold text-brand-900">Application History</h1></div>
      {error && <p className="text-rejected">{error}</p>}
      {!error && applications.length === 0 && (
        <p className="text-slate-500">No applications yet. <Link to="/apply" className="text-brand-600 hover:underline">Apply now</Link>.</p>
      )}
      {applications.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">Application ID</th><th className="px-4 py-3 font-medium">Date</th><th className="px-4 py-3 font-medium">Loan Amount</th>
                <th className="px-4 py-2 font-medium">Decision</th>
                <th className="px-4 py-2 font-medium">Probability</th>
                <th className="px-4 py-2 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {applications.map((app) => (
                <tr key={app.id} className="border-t border-slate-100">
                  <td className="px-4 py-3 font-medium text-slate-700">{app.application_id}</td><td className="px-4 py-3 text-slate-600">{new Date(app.created_at).toLocaleDateString('en-IN')}</td><td className="px-4 py-3 text-slate-600">{formatINR(Number(app.features.credit_amount) * 100)}</td>
                  <td className="px-4 py-3"><StatusBadge value={app.prediction?.decision ?? 'Under Review'} /></td>
                  <td className="px-4 py-2 text-slate-600">
                    {app.prediction ? `${(app.prediction.probability * 100).toFixed(1)}%` : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <Link to={`/results/${app.id}`} className="text-brand-600 hover:underline">View</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
