import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { ArrowLeft, Building2, Landmark, Mail, MapPin, School, ShieldCheck, Sparkles } from 'lucide-react';
import { errorMessage } from '../api/client';
import { useAuth } from '../auth/auth';
import { useDemoMode, type DemoAccount } from '../auth/demo';
import { Hero3D } from '../components/Lazy3D';
import { BrandMark } from '../components/Sidebar';
import { ROLE_LABELS } from '../utils/formatters';

const ROLE_ICON = { MINISTRY: Landmark, STATE_OFFICER: Building2, DISTRICT_OFFICER: MapPin, INSTITUTE_OFFICER: School } as const;

/** The demo switch shown on every sign-in page. */
export function DemoToggle({ enabled, onChange }: { enabled: boolean; onChange: (on: boolean) => void }) {
  return (
    <button type="button" role="switch" aria-checked={enabled} onClick={() => onChange(!enabled)}
      className={`group inline-flex items-center gap-2.5 rounded-full py-1.5 pl-1.5 pr-3.5 text-sm font-medium ring-1 transition ${
        enabled ? 'bg-saffron-500/10 text-ink-900 ring-saffron-500/40' : 'bg-white text-slate-600 ring-slate-200 hover:ring-slate-300'}`}>
      <span className={`relative h-6 w-11 rounded-full transition ${enabled ? 'bg-saffron-500' : 'bg-slate-300'}`}>
        <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-all ${enabled ? 'left-[22px]' : 'left-0.5'}`} />
      </span>
      Demo mode {enabled ? 'on' : 'off'}
    </button>
  );
}

function CodeInput({ value, onChange, disabled }: { value: string; onChange: (v: string) => void; disabled?: boolean }) {
  const refs = useRef<(HTMLInputElement | null)[]>([]);
  const digits = value.padEnd(6, ' ').slice(0, 6).split('');
  const set = (i: number, d: string) => {
    const next = digits.map((c, j) => (j === i ? d : c)).join('').replace(/ /g, '');
    onChange(next.slice(0, 6));
  };
  const onKey = (i: number, e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && !digits[i].trim() && i > 0) refs.current[i - 1]?.focus();
  };
  return (
    <div className="flex justify-between gap-2" role="group" aria-label="6-digit sign-in code">
      {digits.map((d, i) => (
        <input key={i} ref={(el) => { refs.current[i] = el; }} value={d.trim()} disabled={disabled}
          inputMode="numeric" autoComplete={i === 0 ? 'one-time-code' : 'off'} maxLength={6} aria-label={`Digit ${i + 1}`}
          className="h-14 w-full min-w-0 rounded-xl border border-slate-300 bg-white text-center text-2xl font-semibold text-ink-900 shadow-sm outline-none transition focus:border-saffron-500 focus:ring-4 focus:ring-saffron-400/20 disabled:bg-slate-50"
          onKeyDown={(e) => onKey(i, e)}
          onChange={(e) => {
            const typed = e.target.value.replace(/\D/g, '');
            if (typed.length > 1) { onChange(typed.slice(0, 6)); refs.current[Math.min(5, typed.length - 1)]?.focus(); return; }
            set(i, typed);
            if (typed && i < 5) refs.current[i + 1]?.focus();
          }} />
      ))}
    </div>
  );
}

export default function Login() {
  const { user, requestOtp, verifyOtp } = useAuth();
  const location = useLocation();
  const demo = useDemoMode();
  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState('');
  const [step, setStep] = useState<'email' | 'code'>('email');
  const [usingDemo, setUsingDemo] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [resendIn, setResendIn] = useState(0);

  useEffect(() => {
    if (resendIn <= 0) return;
    const t = window.setTimeout(() => setResendIn((n) => n - 1), 1000);
    return () => window.clearTimeout(t);
  }, [resendIn]);

  if (user) {
    const from = (location.state as { from?: string } | null)?.from ?? '/';
    return <Navigate to={from} replace />;
  }

  const send = async (address: string, viaDemo: boolean) => {
    setBusy(true); setError(null);
    try {
      const message = await requestOtp(address, viaDemo);
      setEmail(address); setUsingDemo(viaDemo); setStep('code');
      if (viaDemo) { setOtp(demo.info?.demo_code ?? ''); setNotice('Demo account: the demo code is filled in.'); }
      else { setOtp(''); setNotice(message); setResendIn(30); }
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const signIn = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true); setError(null);
    try {
      await verifyOtp(email, otp, usingDemo);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const demoOn = demo.enabled;
  const accounts: DemoAccount[] = demo.info?.available ? demo.info.console_accounts : [];
  const primary = 'btn btn-primary w-full !py-3';

  return (
    <div className="grid min-h-dvh bg-white lg:grid-cols-[1.15fr_1fr]">
      <div className="relative min-h-[34vh] lg:min-h-dvh overflow-hidden bg-ink-900">
        <Hero3D className="absolute inset-0" />
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-ink-950/95 via-ink-950/30 to-transparent" />
        <div className="absolute left-6 right-6 bottom-6 lg:left-12 lg:bottom-12 text-white">
          <div className="flex items-center gap-3">
            <BrandMark />
            <div>
              <p className="text-lg font-semibold tracking-tight leading-none">ScholarSetu</p>
              <p className="mt-1 text-xs text-slate-300">Ministry of Tribal Affairs · Scholarships</p>
            </div>
          </div>
          <p className="mt-5 max-w-md text-2xl lg:text-4xl font-semibold leading-tight tracking-tight">
            Verify once, reuse everywhere.
          </p>
          <p className="mt-2 max-w-md text-sm text-slate-300">
            Every tribal student's scholarship in one view, from application to money in the bank.
          </p>
        </div>
      </div>

      <div className="relative flex flex-col bg-[radial-gradient(900px_420px_at_100%_0%,rgb(245_158_11/0.08),transparent_60%)]">
        <div className="tricolour" />
        <div className="flex flex-1 items-center justify-center px-6 py-10 sm:px-12">
        <div className="rise w-full max-w-md">
          <div className="flex items-center justify-between gap-3">
            <span className="inline-flex items-center gap-2 text-saffron-500">
              <ShieldCheck className="h-5 w-5" />
              <span className="text-xs font-semibold uppercase tracking-wider">Officers &amp; Ministry</span>
            </span>
            <DemoToggle enabled={demoOn} onChange={(on) => { demo.setEnabled(on); setStep('email'); setError(null); }} />
          </div>

          {step === 'email' ? (
            <>
              <h1 className="mt-6 text-[28px] font-semibold tracking-tight text-slate-900">Sign in</h1>
              {demoOn ? (
                <>
                  <p className="mt-1 text-[15px] text-slate-500">Choose a demo account. Demo accounts use sample data
                    and the code {demo.info?.demo_code ?? '123456'}.</p>
                  {demo.info && !demo.info.available && (
                    <p className="mt-4 rounded-xl bg-amber-50 p-3 text-sm text-amber-900 ring-1 ring-amber-200">
                      Demo sign-in is switched off on this server. Turn demo mode off to sign in with your email.</p>
                  )}
                  <ul className="mt-6 grid gap-2.5">
                    {accounts.map((a) => {
                      const Icon = ROLE_ICON[a.role as keyof typeof ROLE_ICON] ?? Landmark;
                      return (
                        <li key={a.email}>
                          <button type="button" disabled={busy} onClick={() => send(a.email!, true)}
                            className="group flex w-full items-center gap-3 rounded-2xl border border-slate-200 bg-white p-3.5 text-left shadow-soft transition hover:-translate-y-0.5 hover:border-saffron-400 disabled:opacity-60">
                            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-ink-900 text-saffron-400"><Icon className="h-5 w-5" /></span>
                            <span className="min-w-0 flex-1">
                              <span className="block text-sm font-semibold text-slate-900">{ROLE_LABELS[a.role] ?? a.role}</span>
                              <span className="block truncate text-[13px] text-slate-500">{a.name}</span>
                            </span>
                            <Sparkles className="h-4 w-4 text-slate-300 group-hover:text-saffron-500" />
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                </>
              ) : (
                <form onSubmit={(e) => { e.preventDefault(); send(email.trim().toLowerCase(), false); }} className="mt-1">
                  <p className="text-[15px] text-slate-500">We email a 6-digit code to your official address.</p>
                  <label className="mt-6 block text-sm font-medium text-slate-700">
                    Official email
                    <span className="relative mt-1.5 block">
                      <Mail className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                      <input type="email" autoComplete="username" required value={email}
                        onChange={(e) => setEmail(e.target.value)} placeholder="name@tribal.gov.in"
                        className="input !pl-10" />
                    </span>
                  </label>
                  <button disabled={busy} className={`${primary} mt-4`}>{busy ? 'Sending…' : 'Email me a code'}</button>
                </form>
              )}
            </>
          ) : (
            <form onSubmit={signIn} className="mt-6">
              <button type="button" onClick={() => { setStep('email'); setOtp(''); setError(null); }}
                className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800">
                <ArrowLeft className="h-4 w-4" /> Back
              </button>
              <h1 className="mt-3 text-[28px] font-semibold tracking-tight text-slate-900">Enter your code</h1>
              <p className="mt-1 text-[15px] text-slate-500">
                {usingDemo ? <>Signing in to a demo account: <span className="font-medium text-slate-700">{email}</span></>
                  : <>Sent to <span className="font-medium text-slate-700">{email}</span>. It expires in 5 minutes.</>}
              </p>
              {notice && <p className="mt-4 rounded-xl bg-slate-50 p-3 text-sm text-slate-600 ring-1 ring-slate-200">{notice}</p>}
              <div className="mt-6"><CodeInput value={otp} onChange={setOtp} disabled={busy} /></div>
              <button disabled={busy || otp.length !== 6} className={`${primary} mt-5`}>{busy ? 'Checking…' : 'Sign in'}</button>
              {!usingDemo && (
                <button type="button" disabled={resendIn > 0 || busy} onClick={() => send(email, false)}
                  className="mt-3 w-full text-sm text-slate-500 hover:text-slate-800 disabled:text-slate-400">
                  {resendIn > 0 ? `Resend the code in ${resendIn} s` : 'Resend the code'}
                </button>
              )}
            </form>
          )}
          {error && <p role="alert" className="rise mt-4 rounded-xl bg-rose-50 p-3 text-sm text-rose-800 ring-1 ring-rose-200">{error}</p>}
          <p className="mt-10 text-[13px] text-slate-400">Students and families use the ScholarSetu app and sign in with DigiLocker.</p>
        </div>
        </div>
        <p className="px-6 pb-6 text-center text-[12px] text-slate-400">
          ScholarSetu · Ministry of Tribal Affairs, Government of India · Access is logged and audited</p>
      </div>
    </div>
  );
}
