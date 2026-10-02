import { useEffect, useRef, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { apiClient, onWaking } from '../api/client';

const TYPICAL_SECONDS = 360; // database plus backend start-up, measured at 3 to 8 minutes

/** Shown while the API's database starts after an idle period. Checks every 15 s and tells every page to
 * reload its data the moment ScholarSetu is ready, so officers never have to guess or refresh. */
export default function WakingBanner() {
  const [since, setSince] = useState<number | null>(null);
  const [now, setNow] = useState(Date.now());
  const timer = useRef<number | null>(null);

  useEffect(() => onWaking(() => setSince((s) => s ?? Date.now())), []);

  useEffect(() => {
    if (since === null) return;
    const tick = window.setInterval(() => setNow(Date.now()), 1000);
    const check = async () => {
      try {
        await apiClient.get('/auth/demo', { timeout: 20000 });
        setSince(null);
        window.dispatchEvent(new Event('scholarsetu:ready'));
      } catch {
        timer.current = window.setTimeout(check, 15000);
      }
    };
    timer.current = window.setTimeout(check, 15000);
    return () => {
      window.clearInterval(tick);
      if (timer.current) window.clearTimeout(timer.current);
    };
  }, [since]);

  if (since === null) return null;
  const elapsed = Math.max(0, Math.round((now - since) / 1000));
  const progress = Math.min(95, Math.round((elapsed / TYPICAL_SECONDS) * 100));
  const mm = Math.floor(elapsed / 60);
  const ss = String(elapsed % 60).padStart(2, '0');
  return (
    <div role="status" aria-live="polite" className="sticky top-0 z-50 border-b border-saffron-400/40 bg-ink-900 text-white">
      <div className="mx-auto flex max-w-7xl items-center gap-3 px-4 py-2.5 sm:px-6 lg:px-10">
        <Loader2 className="h-4 w-4 shrink-0 animate-spin text-saffron-400" />
        <p className="flex-1 text-sm">
          <span className="font-semibold">ScholarSetu is starting up</span>
          <span className="text-slate-300"> after being idle to save cost. This usually takes 3 to 8 minutes; this page
            refreshes itself when ready.</span>
        </p>
        <span className="font-mono text-sm tabular-nums text-saffron-400">{mm}:{ss}</span>
      </div>
      <div className="h-1 bg-white/10"><div className="h-1 bg-saffron-400 transition-all duration-1000" style={{ width: `${progress}%` }} /></div>
    </div>
  );
}
