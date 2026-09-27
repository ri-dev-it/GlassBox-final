import { useState, type FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Eye, EyeOff, LockKeyhole, Mail, UserRound } from 'lucide-react';
import { isAxiosError } from 'axios';
import { useAuth } from '../../hooks/useAuth';
import GoogleSignInButton from '../../components/common/GoogleSignInButton';

type SignupRole = 'client' | 'admin';

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [role, setRole] = useState<SignupRole>('client');
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState<string[]>(params.get('error') ? [params.get('error') as string] : []);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setErrors([]);
    if (password !== confirmPassword) { setErrors(['Passwords do not match.']); return; }
    setSubmitting(true);
    try {
      await register(email.trim(), password, fullName.trim(), role);
      navigate('/login?registered=1', { replace: true });
    } catch (error) {
      const data = isAxiosError(error) ? error.response?.data : undefined;
      setErrors(data?.errors ?? (data?.error ? [data.error] : [isAxiosError(error) && !error.response ? 'Unable to connect to backend.' : 'Unable to create your account. Please try again.']));
    } finally { setSubmitting(false); }
  };

  return <main className="mx-auto grid min-h-[calc(100vh-7rem)] max-w-5xl overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-xl shadow-slate-200/60 md:grid-cols-[0.9fr_1fr]">
    <section className="order-2 hidden bg-slate-950 p-10 text-white md:order-1 md:flex md:flex-col md:justify-between"><div><div className="mb-8 flex h-11 w-11 items-center justify-center rounded-xl bg-brand-500 text-lg font-bold">AI</div><p className="text-sm font-semibold uppercase tracking-[0.2em] text-sky-300">Get started</p><h1 className="mt-4 text-4xl font-semibold leading-tight">A clearer way to understand your loan application.</h1></div><div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm leading-6 text-slate-300">Your information is used to create your account and provide transparent, explainable decision insights.</div></section>
    <section className="order-1 flex items-center p-6 sm:p-10 md:order-2"><div className="mx-auto w-full max-w-sm"><p className="text-sm font-semibold text-brand-600">Create your account</p><h2 className="mt-1 text-3xl font-bold tracking-tight text-slate-900">Start with confidence</h2><p className="mt-2 text-sm text-slate-500">Create an account to manage your loan applications.</p>
      <GoogleSignInButton page="register" /><div className="my-5 flex items-center gap-3 text-xs font-medium uppercase tracking-wider text-slate-400"><span className="h-px flex-1 bg-slate-200" />or continue with email<span className="h-px flex-1 bg-slate-200" /></div>
      <form onSubmit={handleSubmit} className="space-y-3"><label className="block text-sm font-medium text-slate-700">Account type<select value={role} onChange={(event) => setRole(event.target.value as SignupRole)} className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm"><option value="client">Applicant</option><option value="admin">Admin / Checker</option></select></label>
        <label className="block text-sm font-medium text-slate-700">Full name<div className="relative mt-1"><UserRound size={18} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" /><input autoComplete="name" required value={fullName} onChange={(event) => setFullName(event.target.value)} className="w-full rounded-xl border border-slate-300 py-2.5 pl-10 pr-3 text-sm" placeholder="Your full name" /></div></label>
        <label className="block text-sm font-medium text-slate-700">Email address<div className="relative mt-1"><Mail size={18} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" /><input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} className="w-full rounded-xl border border-slate-300 py-2.5 pl-10 pr-3 text-sm" placeholder="you@example.com" /></div></label>
        <label className="block text-sm font-medium text-slate-700">Password<div className="relative mt-1"><LockKeyhole size={18} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" /><input type={showPassword ? 'text' : 'password'} autoComplete="new-password" minLength={8} required value={password} onChange={(event) => setPassword(event.target.value)} className="w-full rounded-xl border border-slate-300 py-2.5 pl-10 pr-11 text-sm" placeholder="At least 8 characters" /><button type="button" onClick={() => setShowPassword(!showPassword)} aria-label={showPassword ? 'Hide password' : 'Show password'} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400">{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}</button></div></label>
        <label className="block text-sm font-medium text-slate-700">Confirm password<div className="relative mt-1"><LockKeyhole size={18} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" /><input type="password" autoComplete="new-password" minLength={8} required value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} className="w-full rounded-xl border border-slate-300 py-2.5 pl-10 pr-3 text-sm" placeholder="Confirm your password" /></div></label>
        {errors.length > 0 && <ul role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-rejected">{errors.map((message) => <li key={message}>{message}</li>)}</ul>}<button type="submit" disabled={submitting} className="w-full rounded-xl bg-brand-600 py-3 text-sm font-semibold text-white disabled:opacity-60">{submitting ? 'Creating account…' : 'Create Account'}</button></form><p className="mt-6 text-center text-sm text-slate-500">Already have an account? <Link to="/login" className="font-semibold text-brand-600 hover:underline">Log in</Link></p>
    </div></section>
  </main>;
}
