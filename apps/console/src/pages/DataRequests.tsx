import { useState } from 'react';
import { apiClient, errorMessage } from '../api/client';
import { useApi } from '../hooks/useApi';
import { ApiView, Card, EmptyState, PageHeader } from '../components/States';
import { formatDateTime, humanize } from '../utils/formatters';

interface DataRequest {
  id: string;
  student_id: string;
  student_name: string | null;
  district: string | null;
  kind: 'ERASURE' | 'CORRECTION';
  details: string;
  status: 'OPEN' | 'DONE' | 'DECLINED';
  resolution: string | null;
  created_at: string;
  resolved_at: string | null;
}

function Resolve({ request, onDone }: { request: DataRequest; onDone: () => void }) {
  const [resolution, setResolution] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const decide = async (status: 'DONE' | 'DECLINED') => {
    setBusy(true); setError(null);
    try {
      await apiClient.post(`/data-requests/${request.id}/resolve`, { status, resolution: resolution.trim() });
      onDone();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };
  const ready = resolution.trim().length >= 10;
  return (
    <div className="mt-3 space-y-2">
      <textarea className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" rows={2} maxLength={2000}
        value={resolution} onChange={(e) => setResolution(e.target.value)}
        placeholder="What was done, or why not (the student sees this)" />
      <div className="flex gap-2">
        <button disabled={busy || !ready} onClick={() => decide('DONE')}
          className="rounded-lg px-3 py-2 text-sm font-semibold bg-emerald-700 text-white disabled:opacity-50">Done</button>
        <button disabled={busy || !ready} onClick={() => decide('DECLINED')}
          className="rounded-lg px-3 py-2 text-sm font-semibold border border-slate-300 disabled:opacity-50">Decline</button>
      </div>
      {error && <p className="text-sm text-rose-800" role="alert">{error}</p>}
    </div>
  );
}

/** Students' requests to erase or correct their data (DPDP Act), for officers in their jurisdiction. */
export default function DataRequests() {
  const [status, setStatus] = useState('OPEN');
  const requests = useApi<DataRequest[]>('/data-requests', { status });
  return (
    <div className="space-y-4">
      <PageHeader title="Data requests"
        subtitle="Students' requests to erase or correct their personal data. Records of money paid stay in the ledger by law." />
      <div className="flex gap-2">
        {['OPEN', 'ALL'].map((s) => (
          <button key={s} onClick={() => setStatus(s)}
            className={`rounded-lg px-3 py-1.5 text-sm ${status === s ? 'bg-ink-900 text-white' : 'border border-slate-300'}`}>
            {s === 'OPEN' ? 'Open' : 'All'}
          </button>
        ))}
      </div>
      <ApiView state={requests} isEmpty={(d) => d.length === 0} empty={<EmptyState title="No requests" />}>
        {(rows) => (
          <div className="space-y-3">
            {rows.map((r) => (
              <Card key={r.id}>
                <p className="text-sm font-semibold">{humanize(r.kind)} · {r.student_name} ({r.district})</p>
                <p className="text-xs text-slate-500">{formatDateTime(r.created_at)} · {humanize(r.status)}</p>
                <p className="text-sm mt-2 whitespace-pre-wrap">{r.details}</p>
                {r.resolution && <p className="text-sm mt-2 text-slate-600">Decision: {r.resolution}</p>}
                {r.status === 'OPEN' && <Resolve request={r} onDone={requests.reload} />}
              </Card>
            ))}
          </div>
        )}
      </ApiView>
    </div>
  );
}
