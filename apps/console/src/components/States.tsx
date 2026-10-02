import type { ReactNode } from 'react';
import { AlertTriangle, Inbox, Loader2, RefreshCw } from 'lucide-react';
import type { ApiState } from '../hooks/useApi';

export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="space-y-3 p-1" role="status" aria-label={label}>
      <div className="skeleton h-5 w-1/3" />
      <div className="skeleton h-24 w-full" />
      <div className="skeleton h-5 w-2/3" />
      <span className="sr-only flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> {label}</span>
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rise bg-rose-50/80 border border-rose-200 text-rose-900 rounded-2xl p-4 text-sm flex items-start gap-3 backdrop-blur" role="alert">
      <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
      <div className="flex-1">
        <p className="font-semibold">Could not load this data</p>
        <p className="text-rose-800 mt-0.5">{message}</p>
      </div>
      {onRetry && (
        <button onClick={onRetry} className="flex items-center gap-1 text-xs font-semibold border border-rose-300 rounded px-2 py-1 hover:bg-rose-100">
          <RefreshCw className="w-3 h-3" /> Retry
        </button>
      )}
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="rise rounded-2xl border border-dashed border-slate-300 bg-white/70 p-10 text-center text-sm text-slate-500">
      <span className="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-2xl bg-slate-100"><Inbox className="h-6 w-6 text-slate-400" /></span>
      <p className="font-semibold text-slate-700">{title}</p>
      {hint && <p className="mt-1">{hint}</p>}
    </div>
  );
}

/** Render loading, error or empty states for an API call, and the children only when there is data. */
export function ApiView<T>({ state, isEmpty, empty, children }: {
  state: ApiState<T>;
  isEmpty?: (data: T) => boolean;
  empty?: ReactNode;
  children: (data: T) => ReactNode;
}) {
  if (state.loading) return <Loading />;
  if (state.error) return <ErrorState message={state.error} onRetry={state.reload} />;
  if (state.data === null) return <Loading />;
  if (isEmpty?.(state.data)) return <>{empty ?? <EmptyState title="Nothing to show" />}</>;
  return <>{children(state.data)}</>;
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="rise flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3 mb-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-[30px] sm:leading-9">{title}</h1>
        {subtitle && <p className="mt-1.5 max-w-2xl text-[15px] leading-6 text-slate-500">{subtitle}</p>}
      </div>
      {actions}
    </div>
  );
}

export function Card({ title, children, className = '' }: { title?: string; children: ReactNode; className?: string }) {
  return (
    <section className={`rise card p-5 sm:p-6 ${className}`}>
      {title && <h2 className="mb-4 text-[12px] font-semibold uppercase tracking-[0.08em] text-slate-500">{title}</h2>}
      {children}
    </section>
  );
}
