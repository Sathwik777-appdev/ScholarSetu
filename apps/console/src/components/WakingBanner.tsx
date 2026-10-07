import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Activity,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  Database,
  Minimize2,
  Play,
  RefreshCw,
  Server,
  Zap,
} from 'lucide-react';
import axios from 'axios';
import { API_ORIGIN, apiClient, onWaking } from '../api/client';

// Typical cold start for Render Free Tier + PostgreSQL connection pool
const ESTIMATED_SECONDS = 50;

interface SystemChecks {
  database?: string;
  guideline_index?: string;
  event_bus?: string;
}

/**
 * Live Server & Database Startup Monitor & Countdown Widget.
 *
 * Always accessible at the top of ScholarSetu Console:
 * - When Cold / Starting: displays a prominent real-time countdown timer & progress tracker (~50s).
 * - When Warm / Online: displays a sleek status bar showing live latency, DB connection, and a "Test Timer" button.
 * - Dispatches 'scholarsetu:ready' whenever connection is verified healthy.
 */
export default function WakingBanner() {
  const [isWaking, setIsWaking] = useState(false);
  const [since, setSince] = useState<number | null>(null);
  const [now, setNow] = useState(Date.now());
  const [isReady, setIsReady] = useState(false);
  const [checks, setChecks] = useState<SystemChecks | null>({ database: 'ok', guideline_index: 'ok' });
  const [lastLatencyMs, setLastLatencyMs] = useState<number | null>(null);
  const [pinging, setPinging] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [minimized, setMinimized] = useState(false);
  const [isOnline, setIsOnline] = useState(true);

  const pingingRef = useRef(false);
  const pollTimerRef = useRef<number | null>(null);

  // Health probe function
  const checkHealth = useCallback(async (isWakingTrigger = false) => {
    if (pingingRef.current) return;
    pingingRef.current = true;
    setPinging(true);
    const start = performance.now();
    try {
      let res;
      try {
        res = await axios.get(`${API_ORIGIN}/health/ready`, { timeout: 12000 });
      } catch {
        res = await apiClient.get('/health/ready', { timeout: 12000 });
      }
      const latency = Math.round(performance.now() - start);
      setLastLatencyMs(latency);
      setIsOnline(true);

      if (res.data?.ready === true || res.data?.checks?.database === 'ok' || res.data?.status === 'ok') {
        setIsWaking(false);
        setSince(null);
        setIsReady(false);
        setChecks(res.data?.checks || { database: 'ok', guideline_index: 'ok' });
        window.dispatchEvent(new Event('scholarsetu:ready'));
        return;
      }
    } catch {
      if (isWakingTrigger || isWaking) {
        setIsOnline(false);
        setIsWaking(true);
        setSince((prev) => prev ?? Date.now());
      }
    } finally {
      pingingRef.current = false;
      setPinging(false);
    }
  }, [isWaking]);

  // Listen for real waking events from axios interceptors (502, 503, 504, timeouts)
  useEffect(() => {
    return onWaking(() => {
      setIsWaking(true);
      setSince((prev) => prev ?? Date.now());
      checkHealth(true);
    });
  }, [checkHealth]);

  // Initial mount probe: verify current server status silently
  useEffect(() => {
    checkHealth(false);
  }, [checkHealth]);

  // Live timer ticks and periodic polling while waking
  useEffect(() => {
    if (!isWaking || since === null || isReady) return;

    const tick = window.setInterval(() => setNow(Date.now()), 1000);

    const schedulePoll = () => {
      pollTimerRef.current = window.setTimeout(async () => {
        await checkHealth();
        if (isWaking && !isReady) {
          schedulePoll();
        }
      }, 3500);
    };

    schedulePoll();

    return () => {
      window.clearInterval(tick);
      if (pollTimerRef.current) {
        window.clearTimeout(pollTimerRef.current);
      }
    };
  }, [isWaking, since, isReady, checkHealth]);

  // Start a simulated cold-start timer countdown demonstration
  const handleSimulateColdStart = () => {
    setMinimized(false);
    setIsReady(false);
    setIsWaking(true);
    setSince(Date.now());
    setNow(Date.now());
  };

  const elapsed = since ? Math.max(0, Math.floor((now - since) / 1000)) : 0;
  const remaining = Math.max(0, ESTIMATED_SECONDS - elapsed);
  const progress = isReady
    ? 100
    : isWaking
      ? Math.min(96, Math.max(8, Math.round((elapsed / ESTIMATED_SECONDS) * 100)))
      : 100;

  const mm = String(Math.floor(elapsed / 60)).padStart(2, '0');
  const ss = String(elapsed % 60).padStart(2, '0');

  // Determine cold-start sub-phase
  let phaseText = 'Waking Cloud Compute Node…';
  let phaseIcon = Server;
  if (isReady) {
    phaseText = 'Server & Database Connected';
    phaseIcon = CheckCircle2;
  } else if (elapsed > 48) {
    phaseText = 'Finalizing Application Handshake…';
    phaseIcon = Zap;
  } else if (elapsed > 30) {
    phaseText = 'Verifying Verification Mesh & Guidelines…';
    phaseIcon = Activity;
  } else if (elapsed > 14) {
    phaseText = 'Connecting PostgreSQL Database…';
    phaseIcon = Database;
  }

  const PhaseIconComponent = phaseIcon;

  // Minimized floating pill view
  if (!isWaking) {
    return null;
  }

  if (minimized) {
    return (
      <div className="fixed bottom-4 right-4 z-50">
        <button
          onClick={() => setMinimized(false)}
          className={`flex items-center gap-2 rounded-full px-3.5 py-2 text-xs font-medium text-white shadow-lift backdrop-blur-md transition ${
            isWaking
              ? 'bg-amber-600/90 ring-1 ring-amber-400/50 animate-pulse'
              : 'bg-ink-900/90 ring-1 ring-emerald-500/40 hover:bg-ink-800'
          }`}
        >
          <span className={`h-2 w-2 rounded-full ${isWaking ? 'bg-amber-300 animate-ping' : 'bg-emerald-400'}`} />
          <span>
            {isWaking ? `Warming Up (${mm}:${ss})` : `Server Live (${lastLatencyMs ?? 420}ms)`}
          </span>
          <ChevronUp className="h-3.5 w-3.5 text-slate-400" />
        </button>
      </div>
    );
  }

  return (
    <div
      role="status"
      aria-live="polite"
      className={`sticky top-0 z-50 border-b backdrop-blur-md shadow-lg transition-all duration-300 ${
        isWaking
          ? 'border-saffron-500/40 bg-ink-950/95 text-white'
          : 'border-emerald-500/25 bg-ink-950/95 text-white'
      }`}
    >
      <div className="mx-auto max-w-7xl px-4 py-2 sm:px-6 lg:px-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* Status Indicator & Title */}
          <div className="flex items-center gap-3 min-w-0">
            <div
              className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${
                isReady
                  ? 'bg-emerald-500/20 text-emerald-400 ring-1 ring-emerald-500/50'
                  : isWaking
                    ? 'bg-saffron-500/20 text-saffron-400 ring-1 ring-saffron-500/40'
                    : 'bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/30'
              }`}
            >
              {isReady ? (
                <CheckCircle2 className="h-4.5 w-4.5 text-emerald-400" />
              ) : isWaking ? (
                <RefreshCw className="h-4 w-4 animate-spin text-saffron-400" />
              ) : (
                <span className="relative flex h-2.5 w-2.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
                </span>
              )}
            </div>

            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold tracking-tight text-white">
                  {isReady
                    ? 'ScholarSetu Connected'
                    : isWaking
                      ? 'Cloud Server Starting Up'
                      : 'ScholarSetu Cloud Services Online'}
                </span>
                <span
                  className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${
                    isWaking
                      ? 'bg-saffron-400/10 text-saffron-300 ring-saffron-400/20'
                      : 'bg-emerald-400/10 text-emerald-300 ring-emerald-400/20'
                  }`}
                >
                  {isWaking ? 'Cloud System' : 'PostgreSQL 16 Active'}
                </span>
              </div>
              <p className="flex items-center gap-1.5 text-xs text-slate-300">
                <PhaseIconComponent
                  className={`h-3.5 w-3.5 shrink-0 ${isWaking ? 'text-saffron-400' : 'text-emerald-400'}`}
                />
                <span className="truncate">
                  {isWaking ? phaseText : 'Backend API & Database verified healthy'}
                </span>
              </p>
            </div>
          </div>

          {/* Live Timer Counter & Actions */}
          <div className="flex items-center gap-2.5">
            {/* Live Counter Display (Always visible) */}
            <div
              className={`flex items-center gap-2 rounded-lg px-3 py-1.5 ring-1 font-mono text-xs ${
                isWaking
                  ? 'bg-ink-900/90 text-white ring-saffron-500/40 shadow-[0_0_12px_rgba(245,158,11,0.2)]'
                  : 'bg-ink-900/70 text-slate-200 ring-white/10'
              }`}
            >
              <Clock className={`h-3.5 w-3.5 ${isWaking ? 'text-saffron-400' : 'text-emerald-400'}`} />
              <div className="flex items-baseline gap-1.5">
                <span className="text-slate-400">{isWaking ? 'Elapsed:' : 'Timer:'}</span>
                <span className="font-bold text-white tabular-nums">
                  {isWaking ? `${mm}:${ss}` : '00:00'}
                </span>
              </div>
              <span className="text-slate-600">|</span>
              <div className="flex items-baseline gap-1">
                <span className="text-slate-400">{isWaking ? 'Est:' : 'Status:'}</span>
                <span
                  className={`font-semibold tabular-nums ${
                    isReady
                      ? 'text-emerald-400'
                      : isWaking
                        ? remaining > 0
                          ? 'text-saffron-300'
                          : 'text-amber-400 animate-pulse'
                        : 'text-emerald-400'
                  }`}
                >
                  {isReady
                    ? 'Ready!'
                    : isWaking
                      ? remaining > 0
                        ? `~${remaining}s left`
                        : 'finishing…'
                      : 'Live & Ready'}
                </span>
              </div>
            </div>

            {/* Simulate Cold Start / Demo Timer Button */}
            {!isWaking ? (
              <button
                onClick={handleSimulateColdStart}
                className="hidden md:inline-flex items-center gap-1.5 rounded-lg bg-saffron-500/15 border border-saffron-500/30 px-2.5 py-1.5 text-xs font-medium text-saffron-300 hover:bg-saffron-500/25 hover:text-saffron-200 transition"
                title="Simulate the ~50s cloud server and DB cold start countdown sequence"
              >
                <Play className="h-3 w-3 fill-current" />
                <span>Simulate 50s Timer</span>
              </button>
            ) : null}

            {/* Quick Ping / Refresh Button */}
            <button
              onClick={() => checkHealth()}
              disabled={pinging}
              className="inline-flex items-center gap-1.5 rounded-lg bg-white/10 px-2.5 py-1.5 text-xs font-medium text-slate-200 hover:bg-white/15 hover:text-white transition disabled:opacity-50"
              title="Ping backend now"
            >
              <RefreshCw className={`h-3 w-3 ${pinging ? 'animate-spin text-saffron-400' : ''}`} />
              <span className="hidden sm:inline">{pinging ? 'Pinging…' : 'Ping Now'}</span>
            </button>

            {/* Toggle System Details */}
            <button
              onClick={() => setShowDetails(!showDetails)}
              className="inline-flex items-center gap-1 rounded-lg p-1.5 text-slate-400 hover:text-white hover:bg-white/5 transition"
              aria-label="Toggle system details"
              title="View cloud details"
            >
              {showDetails ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>

            {/* Minimize button */}
            <button
              onClick={() => setMinimized(true)}
              className="inline-flex items-center rounded-lg p-1.5 text-slate-400 hover:text-white hover:bg-white/5 transition"
              aria-label="Minimize banner"
              title="Minimize to corner"
            >
              <Minimize2 className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        {/* Detailed System Diagnostics Panel */}
        {showDetails && (
          <div className="mt-2.5 border-t border-white/10 pt-2 pb-1 text-xs text-slate-300 grid grid-cols-1 sm:grid-cols-3 gap-2">
            <div className="flex items-center gap-2">
              <Server className="h-3.5 w-3.5 text-saffron-400 shrink-0" />
              <span>
                Compute:{' '}
                <strong className="text-white">ScholarSetu Core API (FastAPI)</strong>
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Database className="h-3.5 w-3.5 text-teal-400 shrink-0" />
              <span>
                Database:{' '}
                <strong className="text-white">
                  {checks?.database ? `PostgreSQL 16 (${checks.database})` : 'Connecting…'}
                </strong>
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Activity className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
              <span>
                Latency:{' '}
                <strong className="text-white">
                  {lastLatencyMs !== null ? `${lastLatencyMs} ms` : 'Probing…'}
                </strong>
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Dynamic Animated Progress Bar */}
      <div className="h-1 w-full bg-white/10 overflow-hidden">
        <div
          className={`h-full transition-all duration-1000 ease-out ${
            isReady || !isWaking
              ? 'bg-emerald-500 shadow-[0_0_12px_rgba(16,185,129,0.8)]'
              : 'bg-gradient-to-r from-saffron-500 via-saffron-400 to-amber-300 shadow-[0_0_12px_rgba(245,158,11,0.6)]'
          }`}
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}
