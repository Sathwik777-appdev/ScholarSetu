import type { ReactNode } from 'react';
import { AlertTriangle, Inbox, Loader2, RefreshCw } from 'lucide-react';
import type { ApiState } from '../hooks/useApi';

export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-slate-500 p-6" role="status">
      <Loader2 className="w-4 h-4 animate-spin" /> {label}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="bg-rose-50 border border-rose-200 text-rose-900 rounded-lg p-4 text-sm flex items-start gap-3" role="alert">
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
    <div className="border border-dashed border-slate-300 rounded-lg p-8 text-center text-sm text-slate-500">
      <Inbox className="w-6 h-6 mx-auto mb-2 text-slate-400" />
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
    <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-2 mb-5">
      <div>
        <h1 className="text-xl font-bold text-slate-900 tracking-tight">{title}</h1>
        {subtitle && <p className="text-sm text-slate-600 mt-0.5">{subtitle}</p>}
      </div>
      {actions}
    </div>
  );
}

export function Card({ title, children, className = '' }: { title?: string; children: ReactNode; className?: string }) {
  return (
    <section className={`bg-white rounded-lg border border-slate-200 p-4 ${className}`}>
      {title && <h2 className="text-sm font-bold text-slate-800 mb-3">{title}</h2>}
      {children}
    </section>
  );
}
