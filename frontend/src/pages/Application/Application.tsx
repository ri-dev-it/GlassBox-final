import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { isAxiosError } from 'axios';
import { FEATURES, FEATURE_KEYS, emptyApplicantForm } from '../../utils/featureConfig';
import FeatureField from '../../components/forms/FeatureField';
import { applicationApi } from '../../services/api';
import DocumentVerificationSection from '../../components/forms/DocumentVerificationSection';
import type { LoanType } from '../../types';

const LOANS: Array<{ value: LoanType; label: string; accent: string; fields: Array<[string, string]> }> = [
  { value: 'PERSONAL_LOAN', label: 'Personal Loan', accent: 'border-sky-500', fields: [['loan_purpose_note', 'Purpose of loan']] },
  { value: 'CAR_LOAN', label: 'Car Loan', accent: 'border-cyan-500', fields: [['vehicle_make_model', 'Vehicle make and model'], ['vehicle_price', 'Vehicle price (₹)']] },
  { value: 'BIKE_LOAN', label: 'Bike Loan', accent: 'border-teal-500', fields: [['vehicle_make_model', 'Bike make and model'], ['vehicle_price', 'Bike price (₹)']] },
  { value: 'HOME_LOAN', label: 'Home Loan', accent: 'border-violet-500', fields: [['property_location', 'Property location'], ['property_value', 'Property value (₹)']] },
  { value: 'BUSINESS_CAPITAL', label: 'Business / Merchant Capital', accent: 'border-amber-500', fields: [['business_name', 'Business name'], ['monthly_turnover', 'Monthly turnover (₹)']] },
  { value: 'EDUCATION_LOAN', label: 'Education Loan', accent: 'border-indigo-500', fields: [['institution_name', 'Institution name'], ['course_name', 'Course and programme']] },
];

function validateField(name: string, value: string): string | undefined {
  const def = FEATURES[name];
  if (!value) return 'Required.';
  if (def.category === 'numeric') {
    const num = Number(value);
    if (Number.isNaN(num)) return 'Must be a number.';
    if (def.min !== undefined && num < def.min) return `Must be >= ${def.min}.`;
    if (def.max !== undefined && num > def.max) return `Must be <= ${def.max}.`;
  } else if (def.options && !def.options.includes(value)) {
    return 'Invalid selection.';
  }
  return undefined;
}

export default function Application() {
  const navigate = useNavigate();
  const [form, setForm] = useState<Record<string, string>>(emptyApplicantForm());
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [loanType, setLoanType] = useState<LoanType>('PERSONAL_LOAN');
  const [details, setDetails] = useState<Record<string, string>>({});
  const loan = LOANS.find(item => item.value === loanType)!;

  const handleChange = (name: string, value: string) => {
    setForm((prev) => ({ ...prev, [name]: value }));
    setFieldErrors((prev) => ({ ...prev, [name]: '' }));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitError(null);

    const errors: Record<string, string> = {};
    for (const key of FEATURE_KEYS) {
      const err = validateField(key, form[key]);
      if (err) errors[key] = err;
    }
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) {
      setSubmitError('Please complete all required fields.');
      const first = Object.keys(errors)[0];
      document.getElementById(first)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      window.setTimeout(() => document.getElementById(first)?.focus(), 300);
      return;
    }

    setSubmitting(true);
    try {
      const payload: Record<string, string | number> = {};
      for (const key of FEATURE_KEYS) {
        payload[key] = FEATURES[key].category === 'numeric' ? Number(form[key]) : form[key];
      }
      const result = await applicationApi.submit({ ...payload, loan_type: loanType, submission_details: details } as unknown as import('../../types').ApplicantFeatures);
      navigate(`/results/${result.application.id}`);
    } catch (err) {
      const message = isAxiosError(err)
        ? err.response?.data?.errors?.join(' ') ?? err.response?.data?.error ?? 'Submission failed.'
        : 'Submission failed.';
      setSubmitError(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-5xl"><div className={`mb-7 border-l-4 pl-4 ${loan.accent}`}><p className="text-sm font-medium text-sky-700">Loan assessment</p><h1 className="mt-1 text-3xl font-bold tracking-tight text-[#102a4c]">New Loan Application</h1><p className="mt-2 text-slate-500">Choose a loan type, then provide the relevant application details. The existing risk model is reused.</p></div>
      <form onSubmit={handleSubmit} className="space-y-5" noValidate>
        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><label className="block text-sm font-semibold text-slate-800">Loan type<select value={loanType} onChange={e => { setLoanType(e.target.value as LoanType); setDetails({}); }} className="mt-2 block w-full rounded-md border border-slate-300 p-2"><option value="PERSONAL_LOAN">Personal Loan</option><option value="CAR_LOAN">Car Loan</option><option value="BIKE_LOAN">Bike Loan</option><option value="HOME_LOAN">Home Loan</option><option value="BUSINESS_CAPITAL">Business / Merchant Capital</option><option value="EDUCATION_LOAN">Education Loan</option></select></label><div className="mt-4 grid gap-4 md:grid-cols-2">{loan.fields.map(([key, label]) => <label key={key} className="text-sm font-medium text-slate-700">{label}<input required value={details[key] ?? ''} onChange={e => setDetails(d => ({ ...d, [key]: e.target.value }))} className="mt-1 block w-full rounded-md border border-slate-300 p-2" /></label>)}</div></section>
        {(['Applicant', 'Financial', 'Loan', 'Assets'] as const).map(section => <section key={section} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"><h2 className="text-lg font-semibold text-slate-800">{section} Information</h2><div className="mt-5 grid gap-5 md:grid-cols-2">{FEATURE_KEYS.filter(key => FEATURES[key].section === section).map(key => <FeatureField key={key} name={key} def={FEATURES[key]} value={form[key]} error={fieldErrors[key]} onChange={handleChange} />)}</div></section>)}
        <DocumentVerificationSection />
        {submitError && <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700" role="alert">{submitError}</p>}
        <button type="submit" disabled={submitting} className="flex w-full items-center justify-center rounded-lg bg-[#0d3b70] py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-[#092e57] disabled:cursor-not-allowed disabled:opacity-60">{submitting ? 'Analyzing credit application…' : 'Analyze Application'}</button>
      </form>
    </div>
  );
}
