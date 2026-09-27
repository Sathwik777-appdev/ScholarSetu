import type { LucideIcon } from 'lucide-react';

interface StatCardProps {
  name: string;
  value: string | number;
  icon: LucideIcon;
  hint?: string;
  tone?: 'default' | 'good' | 'bad';
}

export default function StatCard({ name, value, icon: Icon, hint, tone = 'default' }: StatCardProps) {
  const iconColor = tone === 'good' ? 'bg-emerald-600' : tone === 'bad' ? 'bg-rose-600' : 'bg-slate-800';
  return (
    <div className="rounded-lg bg-white p-4 border border-slate-200">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold uppercase tracking-wider text-slate-500">{name}</span>
        <div className={`rounded-md p-2 text-white ${iconColor}`}>
          <Icon className="h-4 w-4" aria-hidden="true" />
        </div>
      </div>
      <div className="mt-2 text-2xl font-black tracking-tight text-slate-900">{value}</div>
      {hint && <p className="text-xs text-slate-500 mt-1">{hint}</p>}
    </div>
  );
}
