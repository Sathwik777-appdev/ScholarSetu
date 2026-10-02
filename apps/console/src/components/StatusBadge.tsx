import type { CanonicalState } from '../types';
import { STATE_COLORS, stateLabel } from '../utils/formatters';

/** The stage of an application as a coloured pill. Colour never carries the meaning alone: the label is always shown. */
export default function StatusBadge({ status }: { status: CanonicalState | string }) {
  const color = STATE_COLORS[status as CanonicalState] ?? 'bg-slate-100 text-slate-700';
  return <span className={`pill ${color}`}>{stateLabel(status)}</span>;
}
