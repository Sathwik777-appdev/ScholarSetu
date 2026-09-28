import type { CanonicalState, SchemeType } from '../types';

export const formatCurrency = (amount: number | string): string =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(Number(amount));

export const formatDate = (value: string): string =>
  new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(value));

export const formatDateTime = (value: string): string =>
  new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
    .format(new Date(value));

export const humanize = (code: string): string =>
  code.toLowerCase().replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase());

export const STATE_LABELS: Record<CanonicalState, string> = {
  DRAFT: 'Draft',
  SUBMITTED: 'Submitted',
  INSTITUTE_VERIFICATION: 'Institute verification',
  DEFICIENCY_RAISED: 'Deficiency raised',
  RESUBMITTED: 'Resubmitted',
  AUTHORITY_VERIFICATION: 'District/state verification',
  SANCTIONED: 'Sanctioned',
  REJECTED: 'Rejected',
  PAYMENT_INITIATED: 'Payment initiated',
  CREDITED: 'Credited',
  PAYMENT_FAILED: 'Payment failed',
  RENEWAL_DUE: 'Renewal due',
  SURRENDERED: 'Surrendered',
};

export const STATE_COLORS: Record<CanonicalState, string> = {
  DRAFT: 'bg-slate-100 text-slate-700',
  SUBMITTED: 'bg-blue-50 text-blue-800',
  INSTITUTE_VERIFICATION: 'bg-amber-50 text-amber-800',
  DEFICIENCY_RAISED: 'bg-rose-50 text-rose-800',
  RESUBMITTED: 'bg-orange-50 text-orange-800',
  AUTHORITY_VERIFICATION: 'bg-violet-50 text-violet-800',
  SANCTIONED: 'bg-indigo-50 text-indigo-800',
  REJECTED: 'bg-rose-100 text-rose-900',
  PAYMENT_INITIATED: 'bg-teal-50 text-teal-800',
  CREDITED: 'bg-emerald-50 text-emerald-800',
  PAYMENT_FAILED: 'bg-rose-50 text-rose-800',
  RENEWAL_DUE: 'bg-pink-50 text-pink-800',
  SURRENDERED: 'bg-slate-100 text-slate-600',
};

export const SCHEME_LABELS: Record<SchemeType, string> = {
  PRE_MATRIC: 'Pre-Matric',
  POST_MATRIC: 'Post-Matric',
  TOP_CLASS: 'Top Class',
  NFST: 'National Fellowship (NFST)',
  NOS: 'National Overseas (NOS)',
};

export const ROLE_LABELS: Record<string, string> = {
  INSTITUTE_OFFICER: 'Institute nodal officer',
  DISTRICT_OFFICER: 'District welfare officer',
  STATE_OFFICER: 'State officer',
  MINISTRY: 'Ministry (MoTA)',
};

export const stateLabel = (s: string) => STATE_LABELS[s as CanonicalState] ?? humanize(s);
export const schemeLabel = (s: string) => SCHEME_LABELS[s as SchemeType] ?? s;

/** "9 days", "5 h", "1 min": SLA targets are seconds long in demo mode, days long otherwise. */
export function formatDays(days: number): string {
  if (days >= 1) return `${Math.round(days * 10) / 10} day${days >= 1 && days < 1.05 ? '' : 's'}`;
  const hours = days * 24;
  if (hours >= 1) return `${Math.round(hours)} h`;
  return `${Math.max(1, Math.round(hours * 60))} min`;
}
