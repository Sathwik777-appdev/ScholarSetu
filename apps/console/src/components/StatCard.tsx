import React from 'react';
import { LucideIcon } from 'lucide-react';

interface StatCardProps {
  name: string;
  value: string | number;
  icon: LucideIcon;
  change?: string;
  changeType?: 'positive' | 'negative' | 'neutral';
  color?: 'indigo' | 'green' | 'red' | 'blue';
}

export default function StatCard({ name, value, icon: Icon, change, changeType, color = 'indigo' }: StatCardProps) {
  const stylesMap = {
    indigo: {
      bg: 'bg-indigo-50/80',
      border: 'border-indigo-100',
      text: 'text-indigo-600',
      iconBg: 'bg-indigo-600 text-white shadow-xs',
    },
    green: {
      bg: 'bg-emerald-50/80',
      border: 'border-emerald-100',
      text: 'text-emerald-600',
      iconBg: 'bg-emerald-600 text-white shadow-xs',
    },
    red: {
      bg: 'bg-rose-50/80',
      border: 'border-rose-100',
      text: 'text-rose-600',
      iconBg: 'bg-rose-600 text-white shadow-xs',
    },
    blue: {
      bg: 'bg-blue-50/80',
      border: 'border-blue-100',
      text: 'text-blue-600',
      iconBg: 'bg-blue-600 text-white shadow-xs',
    },
  };

  const currentStyle = stylesMap[color] || stylesMap.indigo;

  return (
    <div className="relative overflow-hidden rounded-2xl bg-white p-5 border border-slate-200/80 shadow-2xs hover:shadow-md transition-all duration-200">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold uppercase tracking-wider text-slate-500">{name}</span>
        <div className={`rounded-xl p-2.5 ${currentStyle.iconBg}`}>
          <Icon className="h-5 w-5" aria-hidden="true" />
        </div>
      </div>
      <div className="mt-3 flex items-baseline gap-x-2.5">
        <div className="text-2xl sm:text-3xl font-black tracking-tight text-slate-900">{value}</div>
        {change ? (
          <span
            className={`inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full text-xs font-bold ${
              changeType === 'positive'
                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200/60'
                : changeType === 'negative'
                ? 'bg-rose-50 text-rose-700 border border-rose-200/60'
                : 'bg-slate-50 text-slate-600 border border-slate-200'
            }`}
          >
            {changeType === 'positive' ? '↑' : changeType === 'negative' ? '↓' : ''} {change}
          </span>
        ) : null}
      </div>
    </div>
  );
}
