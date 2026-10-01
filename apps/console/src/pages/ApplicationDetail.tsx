import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, FileText, Link2, ShieldAlert, ShieldCheck } from 'lucide-react';
import { useApi } from '../hooks/useApi';
import { ApiView, Card, EmptyState } from '../components/States';
import StatusBadge from '../components/StatusBadge';
import { formatCurrency, formatDateTime, humanize, schemeLabel } from '../utils/formatters';
import type { Application, ChainVerification, DBTStatus, LedgerEvent } from '../types';
import { useAuth } from '../auth/auth';
import { BankCheckButton, DocumentsPanel, SanctionPanel, StageActions } from '../components/Workbench';
import { openDocument } from '../api/documents';

function ChainStatus({ id }: { id: string }) {
  const chain = useApi<ChainVerification>(`/applications/${id}/verify-chain`);
  return (
    <ApiView state={chain}>
      {(c) => c.valid ? (
        <p className="flex items-center gap-1.5 text-sm text-emerald-800"><ShieldCheck className="w-4 h-4" />
          Hash chain verified just now: {c.events_checked} events, none altered, removed or reordered.</p>
      ) : (
        <p className="flex items-center gap-1.5 text-sm text-rose-800"><ShieldAlert className="w-4 h-4" />
          Hash chain broken at event {c.first_invalid_event_id}: {c.reason}</p>
      )}
    </ApiView>
  );
}

function Payments({ id }: { id: string }) {
  const dbt = useApi<DBTStatus>(`/dbt/status/${id}`);
  return (
    <div className="space-y-3">
    <ApiView state={dbt} isEmpty={(d) => d.payments.length === 0 && !d.latest_health_check}
      empty={<p className="text-sm text-slate-500">Nothing sanctioned yet and no bank check has been run.</p>}>
      {(d) => (
        <div className="space-y-2 text-sm">
          {d.latest_health_check && (
            <p>Last bank check ({formatDateTime(d.latest_health_check.checked_at)}): <strong>{d.latest_health_check.overall_status}</strong>
              {d.latest_health_check.issues.length > 0 && ` — ${d.latest_health_check.issues.map((i) => i.code).join(', ')}`}</p>
          )}
          {d.payments.map((p) => (
            <p key={p.payment_id}>Instalment {p.instalment}: {formatCurrency(p.amount)} · <strong>{humanize(p.state)}</strong>
              {p.failure_code && <span className="text-rose-700"> ({p.failure_code})</span>}</p>
          ))}
        </div>
      )}
    </ApiView>
    <BankCheckButton appId={id} onDone={dbt.reload} />
    </div>
  );
}

export default function ApplicationDetail() {
  const { id = '' } = useParams();
  const app = useApi<Application>(`/applications/${id}`);
  const timeline = useApi<LedgerEvent[]>(`/applications/${id}/timeline`);
  const { user } = useAuth();
  const canSanction = user?.role === 'DISTRICT_OFFICER' || user?.role === 'STATE_OFFICER';
  const refresh = () => { app.reload(); timeline.reload(); };

  return (
    <div className="space-y-4">
      <Link to="/applications" className="inline-flex items-center gap-1 text-xs text-slate-600"><ArrowLeft className="w-3 h-3" /> Applications</Link>
      <ApiView state={app}>
        {(a) => (
          <Card>
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h1 className="text-lg font-bold font-mono">{a.id}</h1>
                <p className="text-sm text-slate-600">{schemeLabel(a.scheme)} · {a.academic_year} · from {a.source_system}{a.source_ref && ` (${a.source_ref})`}</p>
              </div>
              <StatusBadge status={a.canonical_state} />
            </div>
            <p className="text-xs text-slate-500 mt-2">In this stage since {formatDateTime(a.state_changed_at)}</p>
            {a.provisional_flags.length > 0 && <p className="text-xs text-amber-800 mt-1">Flags: {a.provisional_flags.join(', ')}</p>}
          </Card>
        )}
      </ApiView>
      {app.data && (
        <Card title="Your actions"><StageActions key={app.data.canonical_state} app={app.data} onChanged={refresh} /></Card>
      )}
      {app.data && canSanction && app.data.canonical_state === 'AUTHORITY_VERIFICATION' && (
        <Card title="Sanction"><SanctionPanel app={app.data} onChanged={refresh} /></Card>
      )}
      {app.data && <Card title="Student's documents"><DocumentsPanel app={app.data} /></Card>}
      <Card title="Ledger integrity"><ChainStatus id={id} /></Card>
      <Card title="Payments"><Payments id={id} /></Card>
      <Card title="Timeline (from the ledger)">
        <ApiView state={timeline} isEmpty={(d) => d.length === 0} empty={<EmptyState title="No events recorded" />}>
          {(events) => (
            <ol className="relative border-l border-slate-200 ml-2 space-y-4">
              {events.map((e) => (
                <li key={e.event_id} className="ml-4">
                  <span className="absolute -left-1.5 mt-1.5 w-3 h-3 rounded-full bg-slate-400" />
                  <p className="text-sm font-semibold">{humanize(e.type.replace(/([a-z])([A-Z])/g, '$1_$2'))}</p>
                  <p className="text-xs text-slate-500">{formatDateTime(e.occurred_at)} · {e.actor} · via {e.source}</p>
                  {Array.isArray(e.payload.document_ids) && e.payload.document_ids.length > 0 && (
                    <div className="mt-1 flex flex-wrap gap-2">
                      {(e.payload.document_ids as string[]).map((docId) => (
                        <button key={docId} onClick={() => openDocument(docId)}
                          className="inline-flex items-center gap-1 text-xs text-blue-800 underline">
                          <FileText className="w-3 h-3" />Open attached document
                        </button>
                      ))}
                    </div>
                  )}
                  {Object.keys(e.payload).length > 0 && (
                    <pre className="mt-1 text-xs bg-slate-50 border border-slate-200 rounded p-2 overflow-x-auto">{JSON.stringify(e.payload, null, 2)}</pre>
                  )}
                  <p className="text-[10px] font-mono text-slate-400 mt-1 flex items-center gap-1 break-all"><Link2 className="w-3 h-3 shrink-0" />{e.hash}</p>
                </li>
              ))}
            </ol>
          )}
        </ApiView>
      </Card>
    </div>
  );
}
