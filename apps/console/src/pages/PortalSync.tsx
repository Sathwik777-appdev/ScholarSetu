import { useState } from 'react';
import { Link } from 'react-router-dom';
import { apiClient, errorMessage } from '../api/client';
import { useAuth } from '../auth/auth';
import { useApi } from '../hooks/useApi';
import { ApiView, Card, EmptyState, PageHeader } from '../components/States';
import { formatDateTime } from '../utils/formatters';

interface ParkedEvent {
  id: string;
  source_system: string;
  source_ref: string;
  raw_status: string;
  reason: string;
  application_id: string | null;
  created_at: string;
  resolved_at: string | null;
}

interface SyncResult {
  students: number;
  imported: number;
  transitions: number;
  payments_updated: number;
  parked: number;
  errors: string[];
}

/** Ask the scholarship portals for their latest statuses now (the always-on worker also does this every five
 * minutes). State officers and the Ministry only; the API refuses everyone else. */
function SyncNow() {
  const { user } = useAuth();
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<SyncResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  if (user?.role !== 'STATE_OFFICER' && user?.role !== 'MINISTRY') return null;

  const run = async () => {
    setBusy(true); setError(null); setResult(null);
    try {
      setResult((await apiClient.post<SyncResult>('/admin/adapters/sync', undefined, { timeout: 120000 })).data);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card title="Sync now">
      <p className="text-sm text-slate-600">
        Checks every student's applications on the scholarship portals and records what changed. It also runs by itself every
        five minutes.
      </p>
      <button onClick={run} disabled={busy} className="btn btn-primary mt-3">{busy ? 'Syncing…' : 'Sync now'}</button>
      {error && <p role="alert" className="mt-3 text-sm text-rose-800">{error}</p>}
      {result && (
        <div role="status" className="mt-3 text-sm">
          <p>
            {result.students} student(s) checked · {result.imported} application(s) imported · {result.transitions} status change(s)
            · {result.payments_updated} payment(s) updated · {result.parked} status(es) parked.
          </p>
          {result.errors.length > 0 && <p className="mt-1 text-rose-800">Problems: {result.errors.join('; ')}</p>}
        </div>
      )}
    </Card>
  );
}

function Parked() {
  const { user } = useAuth();
  const canResolve = user?.role === 'STATE_OFFICER' || user?.role === 'MINISTRY';
  const [all, setAll] = useState(false);
  const events = useApi<ParkedEvent[]>('/admin/adapters/parked', { include_resolved: all ? 'true' : 'false' });
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const resolve = async (id: string) => {
    setBusy(id); setError(null);
    try {
      await apiClient.post(`/admin/adapters/parked/${id}/resolve`);
      events.reload();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        {[false, true].map((v) => (
          <button key={String(v)} onClick={() => setAll(v)} className={`btn btn-sm ${all === v ? 'btn-primary' : 'btn-outline'}`}>
            {v ? 'All' : 'Open'}
          </button>
        ))}
      </div>
      {error && <p role="alert" className="text-sm text-rose-800">{error}</p>}
      <ApiView state={events} isEmpty={(d) => d.length === 0}
        empty={<EmptyState title="Nothing parked" hint="Every status the scholarship portals reported was understood." />}>
        {(rows) => (
          <div className="space-y-3">
            {rows.map((p) => (
              <Card key={p.id}>
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold">{p.source_system} · {p.source_ref}</p>
                    <p className="text-xs text-slate-500">{formatDateTime(p.created_at)}{p.resolved_at && ` · resolved ${formatDateTime(p.resolved_at)}`}</p>
                  </div>
                  {canResolve && !p.resolved_at && (
                    <button disabled={busy === p.id} onClick={() => resolve(p.id)} className="btn btn-outline btn-sm">
                      {busy === p.id ? 'Saving…' : 'Mark handled'}
                    </button>
                  )}
                </div>
                <p className="mt-2 text-sm">Portal said <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-xs">{p.raw_status}</span></p>
                <p className="mt-1 text-sm text-slate-600 break-words">{p.reason}</p>
                {p.application_id && (
                  <Link to={`/application/${p.application_id}`} className="mt-2 inline-block text-xs text-blue-800 underline">Open application</Link>
                )}
              </Card>
            ))}
          </div>
        )}
      </ApiView>
    </div>
  );
}

/** Statuses the portals reported that ScholarSetu could not place on its own, and a way to ask for a fresh sync. */
export default function PortalSync() {
  return (
    <div className="space-y-6">
      <PageHeader title="Portal sync"
        subtitle="Statuses reported by the scholarship portals. Anything ScholarSetu could not place on its own is parked here for an officer." />
      <SyncNow />
      <Parked />
    </div>
  );
}
