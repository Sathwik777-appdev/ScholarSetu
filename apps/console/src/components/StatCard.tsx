import type { LucideIcon } from 'lucide-react';

interface StatCardProps {
  name: string;
  value: string | number;
  icon: LucideIcon;
  hint?: string;
  tone?: 'default' | 'good' | 'bad';
}

const TONES = {
  default: { bar: 'from-saffron-400 to-saffron-500', icon: 'bg-ink-900 text-saffron-400' },
  good: { bar: 'from-emerald-400 to-teal-500', icon: 'bg-emerald-600 text-white' },
  bad: { bar: 'from-rose-400 to-rose-600', icon: 'bg-rose-600 text-white' },
};

export default function StatCard({ name, value, icon: Icon, hint, tone = 'default' }: StatCardProps) {
  const t = TONES[tone];
  return (
    <div className="rise card card-interactive relative overflow-hidden p-5">
      <div className={`absolute inset-x-0 top-0 h-1 bg-gradient-to-r ${t.bar}`} />
      <div className="flex items-center justify-between gap-3">
        <span className="text-[12px] font-semibold uppercase tracking-wide text-slate-500">{name}</span>
        <div className={`rounded-xl p-2.5 shadow-soft ${t.icon}`}>
          <Icon className="h-4 w-4" aria-hidden="true" />
        </div>
      </div>
      <div className="mt-3 text-[30px] font-semibold leading-none tracking-tight text-slate-900 tabular-nums">{value}</div>
      {hint && <p className="mt-2 text-[13px] text-slate-500">{hint}</p>}
    </div>
  );
}
