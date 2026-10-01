import { useState, type FormEvent } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { ShieldCheck } from 'lucide-react';
import { errorMessage } from '../api/client';
import { useAuth } from '../auth/auth';
import { Hero3D } from '../components/Lazy3D';
import { BrandMark } from '../components/Sidebar';

// Seeded demo officer accounts (scripts/seed_demo.py). Shown only in demo builds (VITE_DEMO_ACCOUNTS=true).
const DEMO_ACCOUNTS = import.meta.env.VITE_DEMO_ACCOUNTS === 'true'
  ? [
      { label: 'Ministry (MoTA)', phone: '9876543240' },
      { label: 'State officer, Jharkhand', phone: '9876543235' },
      { label: 'District officer, Dumka', phone: '9876543230' },
      { label: 'Institute officer, Dumka', phone: '9876543225' },
    ]
  : [];

export default function Login() {
  const { user, requestOtp, verifyOtp } = useAuth();
  const location = useLocation();
  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState('');
  const [step, setStep] = useState<'phone' | 'otp'>('phone');
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (user) {
    const from = (location.state as { from?: string } | null)?.from ?? '/dashboard';
    return <Navigate to={from} replace />;
  }

  const sendCode = async (number: string) => {
    setBusy(true);
    setError(null);
    try {
      setNotice(await requestOtp(number));
      setStep('otp');
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const submitPhone = (e: FormEvent) => {
    e.preventDefault();
    return sendCode(phone);
  };

  const pickDemoAccount = (number: string) => {
    setPhone(number);
    setOtp('');
    return sendCode(number);
  };

  const submitOtp = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await verifyOtp(phone, otp);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const input = 'mt-1.5 w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-[15px] shadow-sm outline-none transition focus:border-saffron-500 focus:ring-4 focus:ring-saffron-400/20';
  const button = 'w-full rounded-xl bg-ink-900 py-2.5 text-sm font-semibold text-white shadow-lift transition hover:bg-ink-800 disabled:opacity-60';

  return (
    <div className="min-h-dvh grid lg:grid-cols-[1.15fr_1fr] bg-white">
      <div className="relative min-h-[38vh] lg:min-h-dvh overflow-hidden bg-ink-900">
        <Hero3D className="absolute inset-0" />
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-ink-950/90 via-ink-950/20 to-transparent" />
        <div className="absolute left-6 right-6 bottom-6 lg:left-12 lg:bottom-12 text-white">
          <div className="flex items-center gap-3">
            <BrandMark />
            <span className="text-lg font-semibold tracking-tight">ScholarSetu</span>
          </div>
          <p className="mt-4 max-w-md text-2xl lg:text-4xl font-semibold leading-tight tracking-tight">
            Verify once, reuse everywhere.
          </p>
          <p className="mt-2 max-w-md text-sm text-slate-300">
            One view of every tribal student's scholarship, from application to money in the bank.
          </p>
        </div>
      </div>

      <div className="flex items-center justify-center px-6 py-10 sm:px-12">
        <div className="rise w-full max-w-sm">
          <div className="flex items-center gap-2 text-saffron-500">
            <ShieldCheck className="w-5 h-5" />
            <span className="text-xs font-semibold uppercase tracking-wider">Officers &amp; ministry</span>
          </div>
          <h1 className="mt-3 text-2xl font-semibold tracking-tight text-slate-900">Sign in</h1>
          <p className="mt-1 text-sm text-slate-500">We send a one-time code to your registered mobile number.</p>

          {step === 'phone' ? (
            <form onSubmit={submitPhone} className="mt-8 space-y-4">
              <label className="block text-sm font-medium text-slate-700">
                Mobile number
                <input
                  type="tel" inputMode="numeric" autoComplete="tel" required pattern="[0-9]{10}"
                  value={phone} onChange={(e) => setPhone(e.target.value.trim())}
                  className={input} placeholder="10-digit number"
                />
              </label>
              <button disabled={busy} className={button}>{busy ? 'Sending…' : 'Send code'}</button>
              {DEMO_ACCOUNTS.length > 0 && (
                <div className="pt-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Demo accounts</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {DEMO_ACCOUNTS.map((a) => (
                      <button key={a.phone} type="button" disabled={busy} onClick={() => pickDemoAccount(a.phone)}
                        className="rounded-full bg-white px-3 py-1.5 text-xs font-medium text-slate-700 ring-1 ring-slate-200 hover:ring-saffron-400 disabled:opacity-60">
                        {a.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </form>
          ) : (
            <form onSubmit={submitOtp} className="mt-8 space-y-4">
              {notice && <p className="rounded-xl bg-slate-50 p-3 text-sm text-slate-600 ring-1 ring-slate-200">{notice}</p>}
              {DEMO_ACCOUNTS.some((a) => a.phone === phone) && (
                <p className="text-xs text-slate-500">Demo account: the code is <span className="font-semibold">123456</span>.</p>
              )}
              <label className="block text-sm font-medium text-slate-700">
                One-time code
                <input
                  type="text" inputMode="numeric" autoComplete="one-time-code" required pattern="[0-9]{6}"
                  value={otp} onChange={(e) => setOtp(e.target.value.trim())}
                  className={`${input} tracking-[0.5em] text-center font-semibold`}
                />
              </label>
              <button disabled={busy} className={button}>{busy ? 'Checking…' : 'Sign in'}</button>
              <button type="button" onClick={() => { setStep('phone'); setOtp(''); }} className="w-full text-sm text-slate-500 hover:text-slate-800">
                Use a different number
              </button>
            </form>
          )}
          {error && <p role="alert" className="rise mt-4 rounded-xl bg-rose-50 p-3 text-sm text-rose-800 ring-1 ring-rose-200">{error}</p>}
          <p className="mt-10 text-xs text-slate-400">Students and families use the ScholarSetu mobile app.</p>
        </div>
      </div>
    </div>
  );
}
