import { useState, type FormEvent } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { ShieldCheck } from 'lucide-react';
import { errorMessage, useAuth } from '../auth/AuthContext';

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

  const submitPhone = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setNotice(await requestOtp(phone));
      setStep('otp');
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
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

  return (
    <div className="min-h-screen bg-slate-100 flex items-center justify-center p-4">
      <div className="w-full max-w-sm bg-white rounded-lg border border-slate-200 p-6 shadow-sm">
        <div className="flex items-center gap-2 mb-1">
          <ShieldCheck className="w-5 h-5 text-slate-800" />
          <h1 className="text-lg font-bold text-slate-900">ScholarSetu console</h1>
        </div>
        <p className="text-xs text-slate-500 mb-5">For institute, district and state officers and the Ministry of Tribal Affairs.</p>

        {step === 'phone' ? (
          <form onSubmit={submitPhone} className="space-y-3">
            <label className="block text-xs font-semibold text-slate-700">
              Registered mobile number
              <input
                type="tel" inputMode="numeric" autoComplete="tel" required pattern="[0-9]{10}"
                value={phone} onChange={(e) => setPhone(e.target.value.trim())}
                className="mt-1 w-full border border-slate-300 rounded px-3 py-2 text-sm"
                placeholder="10-digit mobile number"
              />
            </label>
            <button disabled={busy} className="w-full bg-slate-900 text-white rounded py-2 text-sm font-semibold disabled:opacity-60">
              {busy ? 'Sending…' : 'Send OTP'}
            </button>
          </form>
        ) : (
          <form onSubmit={submitOtp} className="space-y-3">
            {notice && <p className="text-xs text-slate-600 bg-slate-50 border border-slate-200 rounded p-2">{notice}</p>}
            <label className="block text-xs font-semibold text-slate-700">
              One-time password
              <input
                type="text" inputMode="numeric" autoComplete="one-time-code" required pattern="[0-9]{6}"
                value={otp} onChange={(e) => setOtp(e.target.value.trim())}
                className="mt-1 w-full border border-slate-300 rounded px-3 py-2 text-sm tracking-widest"
              />
            </label>
            <button disabled={busy} className="w-full bg-slate-900 text-white rounded py-2 text-sm font-semibold disabled:opacity-60">
              {busy ? 'Checking…' : 'Sign in'}
            </button>
            <button type="button" onClick={() => { setStep('phone'); setOtp(''); }} className="w-full text-xs text-slate-500">
              Use a different number
            </button>
          </form>
        )}
        {error && <p role="alert" className="mt-3 text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded p-2">{error}</p>}
      </div>
    </div>
  );
}
