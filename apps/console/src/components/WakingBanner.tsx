import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Activity,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  Database,
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
 * Automatically detects when ScholarSetu's backend / database is waking from idle,
 * displays a real-time countdown & progress bar, and signals all pages via 'scholarsetu:ready'
 * when all services are healthy and responsive.
 */
export default function WakingBanner() {
  const [since, setSince] = useState<number | null>(null);
  const [now, setNow] = useState(Date.now());
  const [isReady, setIsReady] = useState(false);
  const [checks, setChecks] = useState<SystemChecks | null>(null);
  const [lastLatencyMs, setLastLatencyMs] = useState<number | null>(null);
  const [pinging, setPinging] = useState(false);
  const [showDetails, setShowDetails] = useState(false);

  const pingingRef = useRef(false);
  const pollTimerRef = useRef<number | null>(null);

  // Health probe function
  const checkHealth = useCallback(async () => {
    if (pingingRef.current) return;
    pingingRef.current = true;
    setPinging(true);
    const start = performance.now();
    try {
      let res;
      try {
        res = await axios.get(`${API_ORIGIN}/health/ready`, { timeout: 8000 });
      } catch {
        res = await apiClient.get('/health/ready', { timeout: 8000 });
      }
      const latency = Math.round(performance.now() - start);
      setLastLatencyMs(latency);

      if (res.data?.ready === true || res.data?.checks?.database === 'ok' || res.data?.status === 'ok') {
        setIsReady(true);
        setChecks(res.data?.checks || { database: 'ok' });
        window.dispatchEvent(new Event('scholarsetu:ready'));

        // Allow user to see the success checkmark before smooth dismiss
        window.setTimeout(() => {
          setSince(null);
          setIsReady(false);
        }, 2200);
        return;
      }
    } catch {
      // Backend still booting or gateway timed out - keep waiting
    } finally {
      pingingRef.current = false;
      setPinging(false);
    }
  }, []);

  // Listen to any API requests that encounter waking errors (502, 503, 504, timeout)
  useEffect(() => {
    return onWaking(() => {
      setSince((prev) => prev ?? Date.now());
    });
  }, []);

  // Proactive probe on initial mount: check if server is currently asleep
  useEffect(() => {
    let active = true;
    const probeInitial = async () => {
      try {
        let res;
        try {
          res = await axios.get(`${API_ORIGIN}/health/ready`, { timeout: 3500 });
        } catch {
          res = await apiClient.get('/health/ready', { timeout: 3500 });
        }
        if (res.data?.ready === true || res.data?.status === 'ok') {
          // Server is warm and ready!
          return;
        }
      } catch {
        // Cold start detected proactively on mount
        if (active) {
          setSince((prev) => prev ?? Date.now());
        }
      }
    };
    probeInitial();
    return () => {
      active = false;
    };
  }, []);

  // Live timer ticks and periodic health polling
  useEffect(() => {
    if (since === null || isReady) return;

    const tick = window.setInterval(() => setNow(Date.now()), 1000);

    const schedulePoll = () => {
      pollTimerRef.current = window.setTimeout(async () => {
        await checkHealth();
        if (since !== null && !isReady) {
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
  }, [since, isReady, checkHealth]);

  if (since === null && !isReady) return null;

  const elapsed = since ? Math.max(0, Math.floor((now - since) / 1000)) : 0;
  const remaining = Math.max(0, ESTIMATED_SECONDS - elapsed);
  const progress = isReady
    ? 100
    : Math.min(96, Math.max(8, Math.round((elapsed / ESTIMATED_SECONDS) * 100)));

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

  return (
    <div
      role="status"
      aria-live="polite"
      className="sticky top-0 z-50 border-b border-saffron-500/30 bg-ink-950/95 text-white backdrop-blur-md shadow-lg transition-all duration-300"
    >
      <div className="mx-auto max-w-7xl px-4 py-2.5 sm:px-6 lg:px-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* Status Indicator & Title */}
          <div className="flex items-center gap-3 min-w-0">
            <div
              className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${
                isReady
                  ? 'bg-emerald-500/20 text-emerald-400 ring-1 ring-emerald-500/50'
                  : 'bg-saffron-500/20 text-saffron-400 ring-1 ring-saffron-500/40'
              }`}
            >
              {isReady ? (
                <CheckCircle2 className="h-4.5 w-4.5 animate-bounce" />
              ) : (
                <RefreshCw className="h-4 w-4 animate-spin" />
              )}
            </div>

            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold tracking-tight text-white">
                  {isReady ? 'ScholarSetu Ready' : 'Cloud Server Starting Up'}
                </span>
                <span className="inline-flex items-center rounded-full bg-saffron-400/10 px-2 py-0.5 text-xs font-medium text-saffron-300 ring-1 ring-inset ring-saffron-400/20">
                  {isReady ? 'Online' : 'Render Free Tier'}
                </span>
              </div>
              <p className="flex items-center gap-1.5 text-xs text-slate-300">
                <PhaseIconComponent className="h-3.5 w-3.5 text-saffron-400 shrink-0" />
                <span className="truncate">{phaseText}</span>
              </p>
            </div>
          </div>

          {/* Live Timer Counter & Actions */}
          <div className="flex items-center gap-3">
            {/* Live Counter Display */}
            <div className="flex items-center gap-2 rounded-lg bg-ink-900/90 px-3 py-1.5 ring-1 ring-white/10 font-mono text-xs">
              <Clock className="h-3.5 w-3.5 text-saffron-400" />
              <div className="flex items-baseline gap-1.5">
                <span className="text-slate-400">Elapsed:</span>
                <span className="font-bold text-white tabular-nums">
                  {mm}:{ss}
                </span>
              </div>
              <span className="text-slate-600">|</span>
              <div className="flex items-baseline gap-1">
                <span className="text-slate-400">Est:</span>
                <span
                  className={`font-semibold tabular-nums ${
                    isReady
                      ? 'text-emerald-400'
                      : remaining > 0
                        ? 'text-saffron-300'
                        : 'text-amber-400 animate-pulse'
                  }`}
                >
                  {isReady ? '0s' : remaining > 0 ? `~${remaining}s left` : 'finishing…'}
                </span>
              </div>
            </div>

            {/* Quick Ping / Refresh Button */}
            <button
              onClick={() => checkHealth()}
              disabled={pinging || isReady}
              className="hidden sm:inline-flex items-center gap-1.5 rounded-lg bg-white/10 px-2.5 py-1.5 text-xs font-medium text-slate-200 hover:bg-white/15 hover:text-white transition disabled:opacity-50"
              title="Test connection now"
            >
              <RefreshCw className={`h-3 w-3 ${pinging ? 'animate-spin text-saffron-400' : ''}`} />
              <span>{pinging ? 'Pinging…' : 'Check Now'}</span>
            </button>

            {/* Toggle System Details */}
            <button
              onClick={() => setShowDetails(!showDetails)}
              className="inline-flex items-center gap-1 rounded-lg p-1.5 text-slate-400 hover:text-white hover:bg-white/5 transition"
              aria-label="Toggle system details"
            >
              {showDetails ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
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
                <strong className="text-white">scholarsetu-api (FastAPI)</strong>
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Database className="h-3.5 w-3.5 text-teal-400 shrink-0" />
              <span>
                Database:{' '}
                <strong className="text-white">
                  {checks?.database ? `PostgreSQL (${checks.database})` : 'Connecting…'}
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
            isReady
              ? 'bg-emerald-500 shadow-[0_0_12px_rgba(16,185,129,0.8)]'
              : 'bg-gradient-to-r from-saffron-500 via-saffron-400 to-amber-300 shadow-[0_0_12px_rgba(245,158,11,0.6)]'
          }`}
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}
