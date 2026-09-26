import { CanonicalState } from '../types';
import { STATUS_COLORS, STATUS_LABELS } from '../utils/constants';

interface StatusBadgeProps {
  status: CanonicalState;
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const colorClass = STATUS_COLORS[status] || 'bg-gray-100 text-gray-800';
  const label = STATUS_LABELS[status] || status;

  return (
    <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset ${colorClass} bg-opacity-10 ring-opacity-20`}>
      {label}
    </span>
  );
}
