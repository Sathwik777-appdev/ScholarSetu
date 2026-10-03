import { useState, type FormEvent } from 'react';
import { apiClient, errorMessage } from '../api/client';
import { Card, PageHeader } from '../components/States';

interface Outreach {
  udise_code: string;
  school_name: string | null;
  unreached_count: number;
  students: { record_ref: string; class_: number; pvtg: boolean }[] | null;
}

function OutreachLookup() {
  const [code, setCode] = useState('');
  const [result, setResult] = useState<Outreach | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const look = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true); setError(null); setResult(null);
    try {
      setResult((await apiClient.get<Outreach>(`/analytics/outreach/${encodeURIComponent(code.trim())}`)).data);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card title="School outreach">
      <p className="text-sm text-slate-600">
        Enrolled ST students of a school who have not applied. Enter the school's UDISE+ code. Only the school's own nodal
        officer sees the individual record references; everyone else sees the count.
      </p>
      <form onSubmit={look} className="mt-3 flex flex-wrap gap-2">
        <input className="input !w-auto min-w-0 flex-1" inputMode="numeric" placeholder="UDISE+ code, e.g. 20140212345"
          value={code} onChange={(e) => setCode(e.target.value)} aria-label="UDISE+ code" />
        <button className="btn btn-primary" disabled={busy || code.trim().length < 5}>{busy ? 'Looking…' : 'Look up'}</button>
      </form>
      {error && <p role="alert" className="mt-3 text-sm text-rose-800">{error}</p>}
      {result && (
        <div className="mt-4 text-sm">
          <p className="font-semibold">{result.school_name ?? result.udise_code}</p>
          <p className="text-slate-700">{result.unreached_count} enrolled ST student(s) have not applied.</p>
          {result.students && result.students.length > 0 && (
            <ul className="mt-2 divide-y divide-slate-100 rounded-lg border border-slate-200">
              {result.students.map((s) => (
                <li key={s.record_ref} className="flex flex-wrap justify-between gap-2 px-3 py-2">
                  <span className="font-mono text-xs break-all">{s.record_ref}</span>
                  <span className="text-xs text-slate-600">Class {s.class_}{s.pvtg ? ' · PVTG' : ''}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </Card>
  );
}

/** Enrolled ST students of a school who have not applied. */
export default function Outreach() {
  return (
    <div className="space-y-6">
      <PageHeader title="Outreach" subtitle="Who in a school has not applied yet, so the school can reach them." />
      <OutreachLookup />
    </div>
  );
}
