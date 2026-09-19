import { useState, type FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Eye, EyeOff, LockKeyhole, Mail } from 'lucide-react';
import { isAxiosError } from 'axios';
import { useAuth } from '../../hooks/useAuth';
import { API_BASE_URL } from '../../services/api';
import { dashboardPath } from '../../utils/roleAccess';

function GoogleMark() {
  return <svg viewBox="0 0 24 24" aria-hidden="true" className="h-5 w-5"><path fill="#4285F4" d="M21.8 12.2c0-.7-.1-1.4-.2-2H12v3.8h5.5a4.7 4.7 0 0 1-2 3.1v2.5h3.2c1.9-1.8 3.1-4.3 3.1-7.4Z" /><path fill="#34A853" d="M12 22c2.7 0 5-.9 6.7-2.4l-3.2-2.5c-.9.6-2 .9-3.5.9-2.6 0-4.8-1.7-5.6-4.1H3.1v2.6A10 10 0 0 0 12 22Z" /><path fill="#FBBC05" d="M6.4 13.9A6 6 0 0 1 6 12c0-.7.1-1.3.4-1.9V7.5H3.1A10 10 0 0 0 2 12c0 1.6.4 3.1 1.1 4.5l3.3-2.6Z" /><path fill="#EA4335" d="M12 6c1.5 0 2.8.5 3.8 1.5l2.9-2.9C17 3 14.7 2 12 2a10 10 0 0 0-8.9 5.5l3.3 2.6C7.2 7.7 9.4 6 12 6Z" /></svg>;
}

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(params.get('error'));
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault(); setError(null); setSubmitting(true);
    try { const loggedInUser = await login(email.trim(), password); navigate(dashboardPath(loggedInUser.role)); }
    catch (err) { const data = isAxiosError(err) ? err.response?.data : undefined; setError(data?.error ?? data?.errors?.[0] ?? 'Unable to log in. Please try again.'); }
    finally { setSubmitting(false); }
  };

  return <main className="mx-auto grid min-h-[calc(100vh-7rem)] max-w-5xl overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-xl shadow-slate-200/60 md:grid-cols-[1fr_0.9fr]">
    <section className="hidden bg-gradient-to-br from-brand-900 via-blue-800 to-sky-600 p-10 text-white md:flex md:flex-col md:justify-between"><div><div className="mb-8 flex h-11 w-11 items-center justify-center rounded-xl bg-white/15 text-lg font-bold">AI</div><p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-100">Loan decision platform</p><h1 className="mt-4 text-4xl font-semibold leading-tight">Welcome back to clear, confident credit decisions.</h1></div><p className="max-w-sm text-sm leading-6 text-blue-100">Securely access your applications, decisions, and clear explanations of every result.</p></section>
    <section className="flex items-center p-6 sm:p-10"><div className="mx-auto w-full max-w-sm"><p className="text-sm font-semibold text-brand-600">Welcome back</p><h2 className="mt-1 text-3xl font-bold tracking-tight text-slate-900">Log in to your account</h2><p className="mt-2 text-sm text-slate-500">Enter your details to continue.</p>
      <button type="button" onClick={() => window.location.assign(`${API_BASE_URL}/auth/google`)} className="mt-7 flex w-full items-center justify-center gap-3 rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-brand-500"><GoogleMark />Continue with Google</button><div className="my-6 flex items-center gap-3 text-xs font-medium uppercase tracking-wider text-slate-400"><span className="h-px flex-1 bg-slate-200" />or continue with email<span className="h-px flex-1 bg-slate-200" /></div>
      <form onSubmit={handleSubmit} className="space-y-4"><label className="block text-sm font-medium text-slate-700">Email address<div className="relative mt-1.5"><Mail size={18} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" /><input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} className="w-full rounded-xl border border-slate-300 py-3 pl-10 pr-3 text-sm outline-none transition focus:border-brand-500 focus:ring-4 focus:ring-brand-100" placeholder="you@example.com" /></div></label><label className="block text-sm font-medium text-slate-700">Password<div className="relative mt-1.5"><LockKeyhole size={18} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" /><input type={showPassword ? 'text' : 'password'} autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} className="w-full rounded-xl border border-slate-300 py-3 pl-10 pr-11 text-sm outline-none transition focus:border-brand-500 focus:ring-4 focus:ring-brand-100" placeholder="Enter your password" /><button type="button" onClick={() => setShowPassword(!showPassword)} aria-label={showPassword ? 'Hide password' : 'Show password'} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}</button></div></label>{error && <p role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-rejected">{error}</p>}<button type="submit" disabled={submitting} className="w-full rounded-xl bg-brand-600 py-3 text-sm font-semibold text-white transition hover:bg-brand-700 focus:outline-none focus:ring-4 focus:ring-brand-200 disabled:cursor-not-allowed disabled:opacity-60">{submitting ? 'Logging in…' : 'Log In'}</button></form><p className="mt-6 text-center text-sm text-slate-500">New here? <Link to="/register" className="font-semibold text-brand-600 hover:text-brand-700">Create an account</Link></p>
    </div></section>
  </main>;
}
