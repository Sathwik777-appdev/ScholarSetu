import { useState } from 'react';
import type { FormEvent } from 'react';
import { AlertTriangle, FileText, Plus, Trash2 } from 'lucide-react';
import axios from 'axios';
import { apiClient, errorMessage } from '../api/client';
import { openDocument } from '../api/documents';
import { useApi } from '../hooks/useApi';
import { useAuth } from '../auth/auth';
import { ApiView } from './States';
import { formatCurrency, formatDateTime, humanize, stateLabel } from '../utils/formatters';
import type { Application, CanonicalState, UserRole } from '../types';

// The moves each officer role may make by hand; the API enforces the same table (ledger/router.py ROLE_TRANSITIONS).
const MOVES: Partial<Record<UserRole, { from: CanonicalState; to: CanonicalState; label: string; needsNote?: boolean }[]>> = {
  INSTITUTE_OFFICER: [
    { from: 'SUBMITTED', to: 'INSTITUTE_VERIFICATION', label: 'Start verification' },
    { from: 'RESUBMITTED', to: 'INSTITUTE_VERIFICATION', label: "Re-check the student's response" },
    { from: 'INSTITUTE_VERIFICATION', to: 'AUTHORITY_VERIFICATION', label: 'Verified: forward to the authority' },
  ],
  DISTRICT_OFFICER: [{ from: 'AUTHORITY_VERIFICATION', to: 'REJECTED', label: 'Reject', needsNote: true }],
  STATE_OFFICER: [{ from: 'AUTHORITY_VERIFICATION', to: 'REJECTED', label: 'Reject', needsNote: true }],
};
const DEFICIENCY_STAGE: Partial<Record<UserRole, CanonicalState>> = {
  INSTITUTE_OFFICER: 'INSTITUTE_VERIFICATION',
  DISTRICT_OFFICER: 'AUTHORITY_VERIFICATION',
  STATE_OFFICER: 'AUTHORITY_VERIFICATION',
};
const DEFICIENCY_CODES = ['DOCUMENT_MISSING', 'DOCUMENT_UNCLEAR', 'NAME_MISMATCH', 'INCOME_PROOF', 'BANK_DETAILS', 'OTHER'];

const inputCls = 'w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-200';
const btnCls = 'inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-semibold disabled:opacity-50';

function Result({ error, done }: { error: string | null; done: string | null }) {
  if (error) return <p className="text-sm text-rose-800 bg-rose-50 border border-rose-200 rounded-lg p-2 mt-2" role="alert">{error}</p>;
  if (done) return <p className="text-sm text-emerald-800 bg-emerald-50 border border-emerald-200 rounded-lg p-2 mt-2">{done}</p>;
  return null;
}

/** Stage moves and deficiencies an officer's role allows for this application right now. */
export function StageActions({ app, onChanged }: { app: Application; onChanged: () => void }) {
  const { user } = useAuth();
  const role = user?.role as UserRole;
  const moves = (MOVES[role] ?? []).filter((m) => m.from === app.canonical_state);
  const canRaise = DEFICIENCY_STAGE[role] === app.canonical_state;
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const [code, setCode] = useState(DEFICIENCY_CODES[0]);
  const [description, setDescription] = useState('');
  const [dueDays, setDueDays] = useState(15);

  const run = async (call: () => Promise<unknown>, success: string) => {
    setBusy(true); setError(null); setDone(null);
    try {
      await call();
      setDone(success);
      onChanged();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  if (!moves.length && !canRaise) {
    return <p className="text-sm text-slate-500">No action for your role while the application is {stateLabel(app.canonical_state).toLowerCase()}.</p>;
  }
  return (
    <div className="space-y-5">
      {moves.length > 0 && (
        <div className="space-y-2">
          <textarea className={inputCls} rows={2} maxLength={1000} value={note} onChange={(e) => setNote(e.target.value)}
            placeholder="Note for the ledger (required to reject; shown in the student's timeline)" />
          <div className="flex flex-wrap gap-2">
            {moves.map((m) => (
              <button key={m.to} disabled={busy || (m.needsNote && note.trim().length < 10)}
                className={`${btnCls} ${m.to === 'REJECTED' ? 'bg-rose-600 text-white hover:bg-rose-700' : 'bg-blue-700 text-white hover:bg-blue-800'}`}
                onClick={() => run(() => apiClient.post(`/officer/applications/${app.id}/transition`,
                  { to_state: m.to, ...(note.trim() ? { note: note.trim() } : {}) }), `Moved to ${stateLabel(m.to)}.`)}>
                {m.label}
              </button>
            ))}
          </div>
          {moves.some((m) => m.needsNote) && note.trim().length < 10 && (
            <p className="text-xs text-slate-500">Rejecting needs a note of at least 10 characters saying why.</p>
          )}
        </div>
      )}
      {canRaise && (
        <form className="space-y-2 border-t border-slate-100 pt-4" onSubmit={(e: FormEvent) => {
          e.preventDefault();
          run(() => apiClient.post(`/officer/applications/${app.id}/deficiencies`,
            { code, description: description.trim(), due_days: dueDays }), 'Deficiency raised; the student has been notified.');
        }}>
          <p className="text-sm font-semibold text-slate-700">Ask the student to fix something</p>
          <div className="grid sm:grid-cols-3 gap-2">
            <select className={inputCls} value={code} onChange={(e) => setCode(e.target.value)} aria-label="Deficiency type">
              {DEFICIENCY_CODES.map((c) => <option key={c} value={c}>{humanize(c)}</option>)}
            </select>
            <label className="flex items-center gap-2 text-sm text-slate-600 sm:col-span-2">Days to respond
              <input type="number" min={1} max={90} className={`${inputCls} w-24`} value={dueDays}
                onChange={(e) => setDueDays(Number(e.target.value))} />
            </label>
          </div>
          <textarea className={inputCls} rows={2} required minLength={10} maxLength={1000} value={description}
            onChange={(e) => setDescription(e.target.value)} placeholder="What the student must do, in plain words" />
          <button disabled={busy || description.trim().length < 10} className={`${btnCls} bg-amber-600 text-white hover:bg-amber-700`}>
            Raise deficiency
          </button>
        </form>
      )}
      <Result error={error} done={done} />
    </div>
  );
}

interface SanctionComponent {
  component: string;
  label: string;
  kind: 'fixed' | 'monthly' | 'actual';
  amount: number | null;
  unit: string;
  note: string | null;
  verified_by_team: boolean;
}
interface SanctionOptions {
  rule_version: string;
  state: CanonicalState;
  components: SanctionComponent[];
  must_surrender: { application_id: string; scheme: string }[];
  flags: string[];
}
interface Row { component: string; description: string; amount: string; months: string; evidence_note: string }

const emptyRow = (): Row => ({ component: '', description: '', amount: '', months: '', evidence_note: '' });

/** Sanction with an instalment plan checked against the scheme's rules; anything outside them needs a reason. */
export function SanctionPanel({ app, onChanged }: { app: Application; onChanged: () => void }) {
  const options = useApi<SanctionOptions>(`/officer/applications/${app.id}/sanction-options`);
  const [rows, setRows] = useState<Row[]>([emptyRow()]);
  const [note, setNote] = useState('');
  const [override, setOverride] = useState('');
  const [needsOverride, setNeedsOverride] = useState(false);
  const [surrender, setSurrender] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  const update = (i: number, patch: Partial<Row>) => setRows((rs) => rs.map((r, j) => (j === i ? { ...r, ...patch } : r)));

  return (
    <ApiView state={options}>
      {(o) => {
        const byPath = Object.fromEntries(o.components.map((c) => [c.component, c]));
        const total = rows.reduce((sum, r) => sum + (Number(r.amount) || 0), 0);
        const submit = async (e: FormEvent) => {
          e.preventDefault();
          setBusy(true); setError(null); setDone(null);
          try {
            await apiClient.post(`/officer/applications/${app.id}/sanction`, {
              instalments: rows.map((r) => ({
                component: r.component, description: r.description.trim() || byPath[r.component]?.label || r.component,
                amount: Number(r.amount),
                ...(r.months ? { months: Number(r.months) } : {}),
                ...(r.evidence_note.trim() ? { evidence_note: r.evidence_note.trim() } : {}),
              })),
              ...(note.trim() ? { note: note.trim() } : {}),
              ...(override.trim() ? { override_reason: override.trim() } : {}),
              ...(surrender && o.must_surrender[0] ? { surrender_application_id: o.must_surrender[0].application_id } : {}),
            });
            setDone(`Sanctioned ${formatCurrency(total)} in ${rows.length} instalment(s).`);
            onChanged();
          } catch (err) {
            if (axios.isAxiosError(err) && (err.response?.data as { detail?: { code?: string } })?.detail?.code === 'OUTSIDE_RULES') {
              setNeedsOverride(true);
            }
            setError(errorMessage(err));
          } finally {
            setBusy(false);
          }
        };
        return (
          <form className="space-y-3" onSubmit={submit}>
            <p className="text-xs text-slate-500">Amounts are checked against rules {o.rule_version}. Each instalment pays one component.</p>
            {o.flags.length > 0 && (
              <p className="text-sm text-amber-900 bg-amber-50 border border-amber-200 rounded-lg p-2 flex gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />Flags on this application: {o.flags.join(', ')}</p>
            )}
            {rows.map((r, i) => {
              const c = byPath[r.component];
              return (
                <div key={i} className="grid sm:grid-cols-12 gap-2 items-start border border-slate-200 rounded-xl p-3">
                  <select required className={`${inputCls} sm:col-span-4`} value={r.component} aria-label={`Instalment ${i + 1} component`}
                    onChange={(e) => update(i, { component: e.target.value })}>
                    <option value="">Component…</option>
                    {o.components.map((x) => <option key={x.component} value={x.component}>{x.label}</option>)}
                  </select>
                  <input className={`${inputCls} sm:col-span-3`} placeholder="Description" value={r.description} maxLength={200}
                    onChange={(e) => update(i, { description: e.target.value })} />
                  <input required type="number" min={1} step="1" className={`${inputCls} sm:col-span-2`} placeholder="Amount ₹"
                    value={r.amount} onChange={(e) => update(i, { amount: e.target.value })} />
                  {c?.kind === 'monthly' ? (
                    <input required type="number" min={1} max={12} className={`${inputCls} sm:col-span-2`} placeholder="Months"
                      value={r.months} onChange={(e) => update(i, { months: e.target.value })} />
                  ) : c?.kind === 'actual' ? (
                    <input required minLength={5} className={`${inputCls} sm:col-span-2`} placeholder="Receipt no." value={r.evidence_note}
                      onChange={(e) => update(i, { evidence_note: e.target.value })} />
                  ) : <span className="sm:col-span-2" />}
                  <button type="button" aria-label="Remove instalment" disabled={rows.length === 1}
                    className="sm:col-span-1 text-slate-400 hover:text-rose-600 disabled:opacity-30 justify-self-end p-2"
                    onClick={() => setRows((rs) => rs.filter((_, j) => j !== i))}><Trash2 className="w-4 h-4" /></button>
                  {c && (
                    <p className="sm:col-span-12 text-xs text-slate-500">
                      {c.kind === 'monthly' && c.amount !== null && `Up to ${formatCurrency(c.amount)} a month (${c.unit}). `}
                      {c.kind === 'fixed' && c.amount !== null && `Up to ${formatCurrency(c.amount)} (${c.unit}). `}
                      {c.kind === 'actual' && `Paid at ${c.note}: give the receipt or fee reference. `}
                      {!c.verified_by_team && <span className="text-amber-800">This amount has not yet been checked against the official document.</span>}
                    </p>
                  )}
                </div>
              );
            })}
            <button type="button" className={`${btnCls} border border-slate-300 text-slate-700 hover:bg-slate-50`}
              onClick={() => setRows((rs) => [...rs, emptyRow()])}><Plus className="w-4 h-4" />Add instalment</button>
            {o.must_surrender.length > 0 && (
              <label className="flex items-start gap-2 text-sm text-amber-900 bg-amber-50 border border-amber-200 rounded-lg p-2">
                <input type="checkbox" className="mt-1" checked={surrender} onChange={(e) => setSurrender(e.target.checked)} />
                The student holds {humanize(o.must_surrender[0].scheme)} ({o.must_surrender[0].application_id}) this year.
                Surrender it with this sanction (its unpaid instalments are cancelled).
              </label>
            )}
            <textarea className={inputCls} rows={2} maxLength={1000} value={note} onChange={(e) => setNote(e.target.value)}
              placeholder="Note for the ledger (optional)" />
            {needsOverride && (
              <textarea className={`${inputCls} border-amber-400`} rows={2} minLength={15} maxLength={1000} value={override}
                onChange={(e) => setOverride(e.target.value)}
                placeholder="This plan is outside the rules. To sanction anyway, explain why (recorded in the ledger with your name)" />
            )}
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm text-slate-700">Total: <strong>{formatCurrency(total)}</strong></p>
              <button disabled={busy || (surrender === false && o.must_surrender.length > 0) || (needsOverride && override.trim().length > 0 && override.trim().length < 15)}
                className={`${btnCls} bg-emerald-700 text-white hover:bg-emerald-800`}>Sanction</button>
            </div>
            <Result error={error} done={done} />
          </form>
        );
      }}
    </ApiView>
  );
}

interface WalletDoc {
  id: string;
  title: string;
  document_type: string;
  source: string;
  source_label: string;
  test_document: boolean;
  verified: boolean;
  mime_type: string;
  uploaded_at: string;
}

export function DocumentsPanel({ app }: { app: Application }) {
  const docs = useApi<WalletDoc[]>(`/officer/applications/${app.id}/documents`);
  return (
    <ApiView state={docs} isEmpty={(d) => d.length === 0}
      empty={<p className="text-sm text-slate-500">The student has no documents in their wallet.</p>}>
      {(d) => (
        <ul className="divide-y divide-slate-100">
          {d.map((doc) => (
            <li key={doc.id} className="py-2 flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="text-sm font-medium truncate">{doc.title}</p>
                <p className="text-xs text-slate-500">
                  {doc.source === 'UPLOAD' ? 'Uploaded by the student' : doc.source_label} · {humanize(doc.document_type)} · {formatDateTime(doc.uploaded_at)}
                  {doc.verified ? <span className="text-emerald-700"> · issuer-signed</span>
                    : doc.test_document ? <span className="text-amber-700"> · test data, not verified</span>
                      : <span> · not verified</span>}
                </p>
              </div>
              <button className={`${btnCls} border border-slate-300 text-slate-700 hover:bg-slate-50 shrink-0`}
                onClick={() => openDocument(doc.id)}><FileText className="w-4 h-4" />Open</button>
            </li>
          ))}
        </ul>
      )}
    </ApiView>
  );
}

/** Run DBT Guardian's bank check now (Aadhaar seeding, account status, name, account type). */
export function BankCheckButton({ appId, onDone }: { appId: string; onDone: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  return (
    <div>
      <button disabled={busy} className={`${btnCls} border border-slate-300 text-slate-700 hover:bg-slate-50`}
        onClick={async () => {
          setBusy(true); setError(null);
          try {
            await apiClient.post(`/dbt/health-check/${appId}`);
            onDone();
          } catch (err) {
            setError(errorMessage(err));
          } finally {
            setBusy(false);
          }
        }}>{busy ? 'Checking…' : 'Run bank check now'}</button>
      <Result error={error} done={null} />
    </div>
  );
}
