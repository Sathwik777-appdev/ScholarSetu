import { Link } from 'react-router-dom';
import { ArrowRight, ClipboardCheck, CreditCard, FileClock, ShieldCheck } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useAuth } from '../auth/auth';
import { useApi } from '../hooks/useApi';
import { ApiView, Card, PageHeader } from '../components/States';
import StatusBadge from '../components/StatusBadge';
import { ROLE_LABELS, formatDays, schemeLabel } from '../utils/formatters';
import type { CanonicalState, OfficerApplication, UserRole } from '../types';

// The stages each role moves on (the API enforces the same rules).
const MY_STAGES: Record<string, CanonicalState[]> = {
  INSTITUTE_OFFICER: ['SUBMITTED', 'RESUBMITTED', 'INSTITUTE_VERIFICATION'],
  DISTRICT_OFFICER: ['AUTHORITY_VERIFICATION', 'PAYMENT_FAILED'],
  STATE_OFFICER: ['AUTHORITY_VERIFICATION', 'PAYMENT_FAILED'],
  MINISTRY: ['AUTHORITY_VERIFICATION', 'PAYMENT_FAILED'],
};
const STAGE_TASK: Partial<Record<CanonicalState, string>> = {
  SUBMITTED: 'Start verification',
  RESUBMITTED: "Check the student's response",
  INSTITUTE_VERIFICATION: 'Finish verification and forward',
  AUTHORITY_VERIFICATION: 'Sanction, ask for a fix, or reject',
  PAYMENT_FAILED: 'Payment failed: check the bank details',
};

function Queue({ stage }: { stage: CanonicalState }) {
  const apps = useApi<OfficerApplication[]>('/applications', { state: stage, limit: 6 });
  return (
    <Card>
      <div className="mb-3 flex items-center justify-between gap-2">
        <div>
          <h2 className="text-[15px] font-semibold text-slate-900">{STAGE_TASK[stage]}</h2>
          <p className="text-[13px] text-slate-500">Longest waiting first</p>
        </div>
        <Link to={`/applications?state=${stage}`} className="inline-flex items-center gap-1 text-[13px] font-medium text-ink-800 hover:underline">
          All <ArrowRight className="h-3.5 w-3.5" /></Link>
      </div>
      <ApiView state={apps} isEmpty={(d) => d.length === 0}
        empty={<p className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-800">Nothing waiting. Well done.</p>}>
        {(rows) => (
          <ul className="divide-y divide-slate-100">
            {rows.map((a) => (
              <li key={a.id}>
                <Link to={`/application/${a.id}`} className="flex items-center gap-3 py-2.5 hover:bg-slate-50 -mx-2 px-2 rounded-lg">
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium text-slate-900">{a.student_name}</span>
                    <span className="block text-[13px] text-slate-500">{schemeLabel(a.scheme)} · {a.district}</span>
                  </span>
                  <StatusBadge status={a.canonical_state} />
                  <span className="w-20 text-right text-[13px] tabular-nums text-slate-600">{formatDays(a.days_in_state)}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </ApiView>
    </Card>
  );
}

function Tile({ to, icon: Icon, label, count }: { to: string; icon: LucideIcon; label: string; count: number | null }) {
  return (
    <Link to={to} className="rise card card-interactive flex items-center gap-3 p-4">
      <span className="grid h-10 w-10 place-items-center rounded-xl bg-ink-900 text-saffron-400"><Icon className="h-5 w-5" /></span>
      <span className="min-w-0 flex-1">
        <span className="block text-2xl font-semibold tabular-nums text-slate-900">{count ?? '–'}</span>
        <span className="block text-[13px] text-slate-500">{label}</span>
      </span>
      <ArrowRight className="h-4 w-4 text-slate-300" />
    </Link>
  );
}

/** Home for every officer: what needs their action today, in their jurisdiction. */
export default function MyWork() {
  const { user } = useAuth();
  const role = (user?.role ?? 'INSTITUTE_OFFICER') as UserRole;
  const analytics = role !== 'INSTITUTE_OFFICER';
  const cases = useApi<unknown[]>('/review/cases', { status: 'PENDING' });
  const requests = useApi<unknown[]>(analytics ? '/data-requests' : null, { status: 'OPEN' });
  const open = useApi<unknown[]>('/applications', { open_only: 'true', limit: 500 });
  const where = role === 'MINISTRY' ? 'All India'
    : [user?.jurisdiction_district, user?.jurisdiction_state].filter(Boolean).join(', ');
  return (
    <div className="space-y-6">
      <PageHeader title={`Good ${new Date().getHours() < 12 ? 'morning' : new Date().getHours() < 17 ? 'afternoon' : 'evening'}`}
        subtitle={`${user?.name ?? ''} · ${ROLE_LABELS[role] ?? role} · ${where}. Here is what needs you today.`} />
      <div className="grid gap-3 sm:grid-cols-3">
        <Tile to="/review-queue" icon={ClipboardCheck} label="Review cases waiting" count={cases.data?.length ?? null} />
        <Tile to="/applications" icon={FileClock} label="Open applications in your area"
          count={open.data ? (open.data.length >= 500 ? 500 : open.data.length) : null} />
        {analytics
          ? <Tile to="/data-requests" icon={ShieldCheck} label="Open data requests" count={requests.data?.length ?? null} />
          : <Tile to="/applications?state=RESUBMITTED" icon={CreditCard} label="Replies to check" count={null} />}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        {(MY_STAGES[role] ?? []).map((s) => <Queue key={s} stage={s} />)}
      </div>
    </div>
  );
}
