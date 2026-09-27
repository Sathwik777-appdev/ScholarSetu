import { useState } from 'react';
import { Link } from 'react-router-dom';
import { CheckCircle2, Clock } from 'lucide-react';
import { apiClient, errorMessage } from '../api/client';
import { useApi } from '../hooks/useApi';
import { ApiView, EmptyState, PageHeader } from '../components/States';
import { formatDateTime, humanize } from '../utils/formatters';
import type { ReviewCase, ReviewCaseStatus, ReviewDecision, ReviewDecisionResponse } from '../types';

const FILTERS: { label: string; value: ReviewCaseStatus | '' }[] = [
  { label: 'Pending', value: 'PENDING' },
  { label: 'Info requested', value: 'INFO_REQUESTED' },
  { label: 'Approved', value: 'APPROVED' },
  { label: 'Rejected', value: 'REJECTED' },
  { label: 'All', value: '' },
];

function hoursLeft(deadline: string): number {
  return Math.round((new Date(deadline).getTime() - Date.now()) / 3_600_000);
}

function SlaChip({ deadline }: { deadline: string }) {
  const h = hoursLeft(deadline);
  const tone = h < 0 ? 'bg-rose-100 text-rose-800' : h < 48 ? 'bg-amber-50 text-amber-800' : 'bg-slate-100 text-slate-700';
  const text = h < 0 ? `Overdue by ${Math.abs(h) >= 48 ? `${Math.round(-h / 24)} days` : `${-h} h`}`
    : h >= 48 ? `${Math.round(h / 24)} days left` : `${h} h left`;
  return <span className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-semibold ${tone}`}><Clock className="w-3 h-3" />{text}</span>;
}

function Evidence({ refs }: { refs: Record<string, unknown>[] }) {
  if (!refs.length) return <p className="text-xs text-slate-500">No source returned evidence for this claim.</p>;
  return (
    <ul className="space-y-1">
      {refs.map((ref, i) => (
        <li key={i} className="text-xs font-mono bg-slate-50 border border-slate-200 rounded p-2 break-all">
          {Object.entries(ref).map(([k, v]) => (
            <span key={k} className="mr-3"><span className="text-slate-500">{k}:</span> {typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
          ))}
        </li>
      ))}
    </ul>
  );
}

function DecisionForm({ item, onDecided }: { item: ReviewCase; onDecided: (r: ReviewDecisionResponse) => void }) {
  const [notes, setNotes] = useState('');
  const [busy, setBusy] = useState<ReviewDecision | null>(null);
  const [error, setError] = useState<string | null>(null);

  const decide = async (decision: ReviewDecision) => {
    setBusy(decision);
    setError(null);
    try {
      const res = await apiClient.post<ReviewDecisionResponse>(`/review/cases/${item.id}/decision`, { decision, notes });
      onDecided(res.data);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  };

  const ready = notes.trim().length >= 3 && busy === null;
  return (
    <div className="space-y-2">
      <label className="block text-xs font-semibold text-slate-700">
        Reason for your decision (recorded in the ledger)
        <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2}
          className="mt-1 w-full border border-slate-300 rounded p-2 text-sm font-normal" />
      </label>
      <div className="flex flex-wrap gap-2">
        <button disabled={!ready} onClick={() => decide('APPROVE')} className="px-3 py-1.5 rounded bg-slate-900 text-white text-xs font-semibold disabled:opacity-50">
          {busy === 'APPROVE' ? 'Recording…' : 'Approve'}
        </button>
        <button disabled={!ready} onClick={() => decide('REQUEST_INFO')} className="px-3 py-1.5 rounded border border-slate-300 text-xs font-semibold disabled:opacity-50">
          {busy === 'REQUEST_INFO' ? 'Recording…' : 'Ask student for more'}
        </button>
        <button disabled={!ready} onClick={() => decide('REJECT')} className="px-3 py-1.5 rounded border border-rose-300 text-rose-700 text-xs font-semibold disabled:opacity-50">
          {busy === 'REJECT' ? 'Recording…' : 'Reject'}
        </button>
      </div>
      {error && <p role="alert" className="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded p-2">Not recorded: {error}</p>}
    </div>
  );
}

export default function ReviewQueue() {
  const [status, setStatus] = useState<ReviewCaseStatus | ''>('PENDING');
  const state = useApi<ReviewCase[]>('/review/cases', { status: status || undefined });
  const [openId, setOpenId] = useState<string | null>(null);
  const [recorded, setRecorded] = useState<ReviewDecisionResponse | null>(null);

  const onDecided = (res: ReviewDecisionResponse) => {
    setRecorded(res);
    setOpenId(null);
    state.reload();
  };

  return (
    <div>
      <PageHeader title="Review queue" subtitle="Claims the verification mesh could not confirm automatically, most urgent first." />

      {recorded && (
        <div role="status" className="mb-4 bg-emerald-50 border border-emerald-200 text-emerald-900 rounded-lg p-3 text-sm flex gap-2">
          <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" />
          <div>
            <p className="font-semibold">Recorded in ledger: {humanize(recorded.case.decision ?? '')} for {recorded.case.application_id}</p>
            <p className="text-xs font-mono mt-0.5">Event {recorded.ledger_event_id}
              {recorded.attestation_id && ` · attestation ${recorded.attestation_id} is ${recorded.attestation_status}`}</p>
          </div>
        </div>
      )}

      <div className="flex flex-wrap gap-1 mb-4">
        {FILTERS.map((f) => (
          <button key={f.label} onClick={() => setStatus(f.value)}
            className={`px-3 py-1 rounded text-xs font-semibold border ${status === f.value ? 'bg-slate-900 text-white border-slate-900' : 'bg-white border-slate-300 text-slate-700'}`}>
            {f.label}
          </button>
        ))}
      </div>

      <ApiView state={state} isEmpty={(d) => d.length === 0}
        empty={<EmptyState title="No cases" hint="Nothing in your jurisdiction matches this filter." />}>
        {(cases) => (
          <ul className="space-y-3">
            {cases.map((c) => (
              <li key={c.id} className="bg-white border border-slate-200 rounded-lg">
                <button onClick={() => setOpenId(openId === c.id ? null : c.id)} className="w-full text-left p-4 flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="font-bold text-slate-900">{c.student_name ?? 'Unknown student'}</p>
                    <p className="text-xs text-slate-500 font-mono">{c.application_id}</p>
                    <p className="text-xs mt-1">
                      <span className="font-semibold">{humanize(c.claim_type)}</span> · {humanize(c.reason)}
                    </p>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    {c.status === 'PENDING' || c.status === 'INFO_REQUESTED'
                      ? <SlaChip deadline={c.sla_deadline} />
                      : <span className="text-xs font-semibold text-slate-600">{humanize(c.status)}</span>}
                    {c.identity_score !== null && (
                      <span className="text-xs text-slate-600">Name similarity {c.identity_score.toFixed(2)} (identity resolver)</span>
                    )}
                  </div>
                </button>
                {openId === c.id && (
                  <div className="border-t border-slate-200 p-4 space-y-3">
                    <div>
                      <p className="text-xs font-bold text-slate-700 mb-1">Why it needs review</p>
                      <p className="text-sm text-slate-700">{c.explanation}</p>
                    </div>
                    <div>
                      <p className="text-xs font-bold text-slate-700 mb-1">Evidence from sources</p>
                      <Evidence refs={c.evidence_refs} />
                    </div>
                    <Link to={`/application/${c.application_id}`} className="inline-block text-xs text-blue-800 underline">Open application timeline</Link>
                    {c.status === 'PENDING' || c.status === 'INFO_REQUESTED' ? (
                      <DecisionForm item={c} onDecided={onDecided} />
                    ) : (
                      <p className="text-xs text-slate-600">
                        Decided {c.decided_at && formatDateTime(c.decided_at)} by {c.decided_by}: “{c.notes}”
                        {c.decision_event_id && <span className="font-mono"> · ledger event {c.decision_event_id}</span>}
                      </p>
                    )}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </ApiView>
    </div>
  );
}
