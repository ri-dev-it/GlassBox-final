import { useEffect, useState } from 'react';
import { documentApi } from '../../services/api';
import type { BankStatementDetail } from '../../types';
import BankStatementDetails from './BankStatementDetails';

export default function BankStatementDocument({ documentId }: { documentId: number }) {
  const [statement, setStatement] = useState<BankStatementDetail | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    let active = true;
    setStatement(null); setError(false);
    documentApi.bankStatement(documentId).then(value => { if (active) setStatement(value); }).catch(() => { if (active) setError(true); });
    return () => { active = false; };
  }, [documentId]);
  if (error) return <p role="alert" className="mt-3 text-sm text-red-700">Could not load parsed bank statement.</p>;
  return statement ? <BankStatementDetails statement={statement} /> : <p className="mt-3 text-sm text-slate-500">Loading parsed bank statement…</p>;
}
