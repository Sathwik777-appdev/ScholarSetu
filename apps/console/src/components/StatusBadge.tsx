import type { CanonicalState } from '../types';
import { STATE_COLORS, stateLabel } from '../utils/formatters';

export default function StatusBadge({ status }: { status: CanonicalState | string }) {
  const color = STATE_COLORS[status as CanonicalState] ?? 'bg-slate-100 text-slate-700';
  return <span className={`inline-flex rounded px-2 py-0.5 text-xs font-semibold ${color}`}>{stateLabel(status)}</span>;
}
