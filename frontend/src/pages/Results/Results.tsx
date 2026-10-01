import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import type { AnalysisReport, ApplicationDetail, GroundedExplanation } from '../../types';
import { applicationApi, explanationApi } from '../../services/api';
import ContributionBarChart from '../../components/charts/ContributionBarChart';
import PlainEnglishCard from '../../components/explanations/PlainEnglishCard';
import CounterfactualTable from '../../components/explanations/CounterfactualTable';
import ComparisonPanel from '../../components/explanations/ComparisonPanel';
import { Download } from 'lucide-react';
import { StatusBadge } from '../../components/common/StatusBadge';
import RiskGauge from '../../components/common/RiskGauge';
import VerificationReportView from '../../components/forms/VerificationReportView';
import BankStatementDetails from '../../components/forms/BankStatementDetails';

export default function Results() {
  const { id } = useParams();
  const [detail, setDetail] = useState<ApplicationDetail | null>(null);
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showTechnical, setShowTechnical] = useState(false);
  const [grounded, setGrounded] = useState<GroundedExplanation | null>(null);

  useEffect(() => {
    if (!id) return;
    applicationApi
      .getById(Number(id))
      .then(setDetail)
      .catch(() => setError('Could not load this application.'));
    applicationApi.report(Number(id)).then(setReport).catch(() => undefined);
    explanationApi.groundedApplication(Number(id)).then(setGrounded).catch(() => undefined);
  }, [id]);

  if (error) return <p className="text-rejected">{error}</p>;
  if (!detail) return <p className="text-slate-500">Loading…</p>;

  const { prediction, shap, lime, comparison, counterfactual } = detail;
  if (!prediction) return <p className="text-slate-500">This application has no prediction yet.</p>;

  const isApproved = prediction.decision === 'APPROVE';
  const isReview = prediction.decision === 'REVIEW';
  const decisionTone = isApproved ? 'border-approved/30' : isReview ? 'border-amber-300' : 'border-rejected/30';
  const decisionTextTone = isApproved ? 'text-approved' : isReview ? 'text-amber-700' : 'text-rejected';
  const downloadReport = async () => {
    try {
      const pdf = await applicationApi.downloadReport(detail.application.id);
      const url = URL.createObjectURL(pdf);
      const link = document.createElement('a'); link.href = url; link.download = `${detail.application.application_id}-assessment.pdf`; link.click(); URL.revokeObjectURL(url);
    } catch {
      setError('Could not download the PDF report.');
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {detail.documentVerification && <VerificationReportView report={detail.documentVerification} showBankStatement={false} />}
      <div className={`rounded-xl border bg-white p-6 shadow-sm ${decisionTone}`}><div className="flex flex-wrap items-start justify-between gap-4"><div>
        <p className="text-sm text-slate-500">{detail.application.application_id} · AI Decision</p>
        <p className={`text-3xl font-bold ${decisionTextTone}`}>
          {prediction.decision}
        </p>
        {isReview && <p className="mt-2 text-sm font-medium text-amber-800">Flagged for manual underwriting review.</p>}
        <p className="mt-2 text-sm text-slate-600">
          Model probability of approval: <strong>{(prediction.probability * 100).toFixed(1)}%</strong>
          <span className="text-slate-400"> -- a statistical estimate, not a certainty.</span>
        </p>
        </div><div className="flex items-center gap-4"><RiskGauge score={prediction.risk_score} change={prediction.probability * 100} /><button onClick={downloadReport} className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"><Download size={16} />Download PDF</button></div></div><div className="mt-5 flex flex-wrap gap-3"><StatusBadge value={prediction.risk_level} /></div></div>

      {report && <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><p className="text-sm font-medium text-sky-700">Stored analysis report</p><h2 className="mt-1 text-lg font-semibold text-slate-800">Top contributing factors</h2><div className="mt-4 space-y-3">{report.factors.map(factor => <article key={factor.feature} className="rounded-lg border border-slate-200 p-4"><div className="flex flex-wrap items-center justify-between gap-2"><h3 className="font-semibold text-slate-800">{factor.label}</h3><span className={`rounded-full px-2 py-1 text-xs font-semibold ${factor.direction === 'positive' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>{factor.direction === 'positive' ? 'Supports approval' : 'Supports rejection'}</span></div><p className="mt-2 text-sm text-slate-600">Applicant value: <strong>{String(factor.value)}</strong></p><p className="mt-1 text-sm text-slate-600">{factor.reason}</p></article>)}</div><div className="mt-5 rounded-lg bg-slate-50 p-4"><h3 className="font-semibold text-slate-800">LIME-based local explanation</h3><p className="mt-2 whitespace-pre-line text-sm text-slate-600">{report.lime.summary}</p></div><div className="mt-4 rounded-lg bg-slate-50 p-4 text-sm text-slate-700"><strong>Risk analysis:</strong> Model-derived risk score {report.risk.score}/100 ({report.risk.level.toLowerCase()} risk).</div><p className="mt-5 text-xs text-slate-500">{report.disclaimer}</p></section>}

      {shap && (
        <section>
          <h2 className="text-lg font-semibold text-slate-800 mb-2">Why did the AI make this decision?</h2>
          <PlainEnglishCard text={shap.plain_english} />
        </section>
      )}

      {(detail.transactionReasoning || detail.documentVerification?.bankStatement) && (
        <section className="rounded-xl border border-emerald-200 bg-emerald-50/60 p-5">
          <p className="text-sm font-medium text-emerald-800">Bank statement decision impact</p>
          <h2 className="mt-1 text-lg font-semibold text-slate-800">Transaction Analysis</h2>
          {detail.transactionReasoning && <>
            <p className="mt-2 text-sm leading-6 text-slate-700">{detail.transactionReasoning.summary}</p>
            <p className="mt-2 text-xs text-slate-600">
              Estimated approval probability: {Math.round(detail.transactionReasoning.baselineApprovalProbability * 100)}% before transaction evidence, {Math.round(detail.transactionReasoning.adjustedApprovalProbability * 100)}% after.
            </p>
            {detail.transactionReasoning.factors.length > 0 && <ul className="mt-3 space-y-2">
              {detail.transactionReasoning.factors.map(factor => <li key={factor.feature} className="border-t border-emerald-200 pt-2 text-sm text-slate-700">
                <strong>{factor.label}</strong>{factor.value != null && <>: {factor.feature.includes('share') || factor.feature.includes('ratio') ? `${(factor.value * 100).toFixed(1)}%` : ['avg_monthly_credits', 'avg_monthly_balance', 'min_monthly_balance'].includes(factor.feature) ? `₹${factor.value.toLocaleString('en-IN')}` : factor.value.toLocaleString('en-IN')}</>} — {factor.reason}
              </li>)}
            </ul>}
          </>}
          {detail.documentVerification?.bankStatement && <BankStatementDetails statement={detail.documentVerification.bankStatement} />}
        </section>
      )}

      {grounded && <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex flex-wrap items-center justify-between gap-2"><h2 className="text-lg font-semibold text-slate-800">Plain-English SHAP explanation</h2><span className={`rounded-full px-2 py-1 text-xs font-semibold ${grounded.source === 'llm' ? 'bg-sky-50 text-sky-700' : 'bg-slate-100 text-slate-700'}`}>{grounded.source === 'llm' ? 'AI-generated' : 'System-generated'}</span></div><p className="mt-3 whitespace-pre-line text-sm text-slate-600">{grounded.text}</p><p className="mt-3 text-xs text-slate-400">Grounded in: {grounded.grounded_in.join(', ')}</p></section>}

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <p className="text-sm font-medium text-sky-700">AI-assisted document verification</p><h2 className="mt-1 text-lg font-semibold text-slate-800">Document Verification</h2>
        {detail.documents?.length ? <div className="mt-4 grid gap-3 sm:grid-cols-2">{detail.documents.map(document => { const status = document.status === 'UPLOADED' ? 'Uploaded' : document.verification?.status ?? document.status; const colour = status === 'VERIFIED' ? 'text-green-700 bg-green-50' : status === 'NEEDS_REVIEW' ? 'text-amber-800 bg-amber-50' : 'text-slate-700 bg-slate-50'; return <div key={document.id} className={`rounded-lg p-3 ${colour}`}><div className="flex justify-between gap-2 text-sm font-semibold"><span>{document.documentType.replace(/_/g, ' ')}</span><span>{status.replace('_', ' ')}</span></div>{document.verification && document.status !== 'UPLOADED' && <p className="mt-1 text-xs">{document.verification.verificationMessage} ({Math.round(document.verification.confidence * 100)}%)</p>}</div>; })}</div> : <p className="mt-3 text-sm text-slate-500">No documents were attached to this application.</p>}
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <p className="text-sm font-medium text-sky-700">AI-Predicted Eligibility</p><h2 className="mt-1 text-lg font-semibold text-slate-800">Bank Eligibility</h2><p className="mt-1 text-xs text-slate-500">Educational AI-generated eligibility estimates only; these are not actual bank approvals or rejections.</p>
        <div className="mt-4 space-y-3">{detail.bankEligibility?.map(bank => { const colour = bank.decision === 'APPROVED' ? 'text-green-700 bg-green-50' : bank.decision === 'NOT_ELIGIBLE' ? 'text-red-700 bg-red-50' : 'text-amber-800 bg-amber-50'; return <article key={bank.bankName} className="rounded-lg border border-slate-200 p-4"><div className="flex flex-wrap items-center justify-between gap-2"><h3 className="font-semibold text-slate-800">{bank.bankName}</h3><span className={`rounded-full px-2 py-1 text-xs font-semibold ${colour}`}>{bank.decision.replace('_', ' ')}</span></div><p className="mt-2 text-sm text-slate-600">General-model probability: <strong>{Math.round(bank.probability * 100)}%</strong></p><p className="mt-2 text-xs text-slate-600"><strong>Reasons:</strong> {bank.reasons.join(' ')}</p><p className="mt-1 text-xs text-slate-600"><strong>Risk indicators:</strong> {bank.riskIndicators.join(' ')}</p><p className="mt-1 text-xs text-slate-500"><strong>Conditions:</strong> {bank.conditions.join(' ')}</p></article>; })}</div>
      </section>

      {shap && (
        <section>
          <h2 className="text-lg font-semibold text-slate-800 mb-2">Key Factors</h2>
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <ContributionBarChart contributions={shap.contributions} />
            <p className="text-xs text-slate-400 mt-2">Green pushes toward approval, red toward rejection.</p>
          </div>
        </section>
      )}

      {counterfactual && (
        <section>
          <h2 className="text-lg font-semibold text-slate-800 mb-2">What could improve my approval chances?</h2><p className="mb-2 text-xs text-slate-500">AI-generated simulation — this is a model-based estimate, not a guaranteed approval.</p>
          <CounterfactualTable counterfactual={counterfactual} />
        </section>
      )}

      <section>
        <button
          onClick={() => setShowTechnical((s) => !s)}
          className="text-sm text-brand-600 hover:underline"
        >
          {showTechnical ? 'Hide' : 'Show'} technical explanation (SHAP vs LIME)
        </button>
        {showTechnical && lime && comparison && (
          <div className="mt-3 rounded-lg border border-slate-200 bg-white p-4 space-y-4">
            <div>
              <h3 className="text-sm font-medium text-slate-700 mb-2">LIME Explanation</h3>
              <ContributionBarChart contributions={lime.contributions} />
            </div>
            <div>
              <h3 className="text-sm font-medium text-slate-700 mb-2">SHAP vs LIME Comparison</h3>
              <ComparisonPanel comparison={comparison} />
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
