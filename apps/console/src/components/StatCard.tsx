import type { LucideIcon } from 'lucide-react';

interface StatCardProps {
  name: string;
  value: string | number;
  icon: LucideIcon;
  hint?: string;
  tone?: 'default' | 'good' | 'bad';
}

const TONES = {
  default: 'from-ink-800 to-ink-700 text-white',
  good: 'from-teal-500 to-emerald-600 text-white',
  bad: 'from-rose-500 to-rose-700 text-white',
};

export default function StatCard({ name, value, icon: Icon, hint, tone = 'default' }: StatCardProps) {
  return (
    <div className="rise group relative overflow-hidden rounded-2xl bg-white p-5 border border-slate-200/70 shadow-soft transition hover:-translate-y-0.5 hover:shadow-lift">
      <div className="pointer-events-none absolute -right-10 -top-10 h-32 w-32 rounded-full bg-gradient-to-br from-saffron-400/10 to-transparent" />
      <div className="flex items-center justify-between">
        <span className="text-[12px] font-semibold uppercase tracking-wide text-slate-500">{name}</span>
        <div className={`rounded-xl p-2.5 bg-gradient-to-br shadow-soft ${TONES[tone]}`}>
          <Icon className="h-4 w-4" aria-hidden="true" />
        </div>
      </div>
      <div className="mt-3 text-[28px] font-semibold tracking-tight text-slate-900 tabular-nums">{value}</div>
      {hint && <p className="text-xs text-slate-500 mt-1">{hint}</p>}
    </div>
  );
}
