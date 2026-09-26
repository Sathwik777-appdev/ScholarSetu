import React from 'react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, 
  ResponsiveContainer, AreaChart, Area 
} from 'recharts';
import { TrendingUp, Clock, Zap, CheckCircle2, ShieldCheck, ArrowUpRight, Award } from 'lucide-react';

const bottleneckData = [
  { stage: 'Draft & Prefill', traditional_days: 12, scholarsetu_days: 0.1 },
  { stage: 'Caste Verification', traditional_days: 21, scholarsetu_days: 0.05 },
  { stage: 'Institute Verification', traditional_days: 14, scholarsetu_days: 3 },
  { stage: 'DBT Sanction Clearance', traditional_days: 18, scholarsetu_days: 1 },
];

const pathwayRetention = [
  { year: '2023', without_setu: 38, with_setu: 38 },
  { year: '2024', without_setu: 41, with_setu: 58 },
  { year: '2025', without_setu: 44, with_setu: 79 },
  { year: '2026', without_setu: 46, with_setu: 94.2 },
];

// Clean Light Tooltip for Analytics
const CustomAnalyticsTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white text-slate-800 p-2.5 rounded border border-slate-200 shadow-sm text-xs space-y-1">
        <p className="font-bold text-slate-900">{label}</p>
        {payload.map((entry: any, index: number) => (
          <div key={index} className="flex items-center justify-between gap-3">
            <span className="text-slate-600 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-xs" style={{ backgroundColor: entry.color }} />
              {entry.name}:
            </span>
            <span className="font-bold text-slate-900 font-mono">{entry.value}{entry.unit || ''}</span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

export default function Analytics() {
  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="bg-white rounded-lg border border-slate-200 p-4 shadow-2xs">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
              <span>SLA Performance & Velocity Evaluation</span>
              <span>•</span>
              <span>Ministry Audit Benchmarks</span>
            </div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight mt-0.5">
              Process Velocity & Pathway Retention Analytics
            </h1>
            <p className="text-xs text-slate-600 mt-0.5">
              Empirical turnaround comparisons between traditional portals and ScholarSetu's Verification Mesh.
            </p>
          </div>
        </div>
      </div>

      {/* Impact Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-2xs">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Average Turnaround</span>
          <div className="text-xl sm:text-2xl font-bold text-emerald-700 mt-1 font-mono">4.1 Days</div>
          <span className="text-[11px] text-slate-500">Down from 65 days</span>
        </div>
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-2xs">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Class 10/11 Retention</span>
          <div className="text-xl sm:text-2xl font-bold text-blue-900 mt-1 font-mono">94.2%</div>
          <span className="text-[11px] text-emerald-700 font-semibold">+48.2% via Auto-Nudge</span>
        </div>
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-2xs">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Attestation Reuses</span>
          <div className="text-xl sm:text-2xl font-bold text-slate-900 mt-1 font-mono">28,400</div>
          <span className="text-[11px] text-slate-500">Zero Tehsildar Re-visits</span>
        </div>
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-2xs">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">DBT Bounces Avoided</span>
          <div className="text-xl sm:text-2xl font-bold text-emerald-700 mt-1 font-mono">950 Cases</div>
          <span className="text-[11px] text-emerald-700 font-semibold">100% Pre-Sanction Cleared</span>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Stage Comparison Chart */}
        <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-2xs space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-slate-900">Days Spent per Stage (Lower is Better)</h2>
              <p className="text-xs text-slate-500">Legacy Portals (Gray) vs ScholarSetu (Navy)</p>
            </div>
            <span className="text-xs font-semibold bg-emerald-50 text-emerald-800 px-2 py-0.5 rounded border border-emerald-200">
              -93% Processing Time
            </span>
          </div>

          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={bottleneckData} margin={{ top: 10, right: 10, left: -20, bottom: 25 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis dataKey="stage" stroke="#64748b" fontSize={10} interval={0} angle={-15} textAnchor="end" tickLine={false} />
                <YAxis stroke="#64748b" fontSize={11} unit="d" tickLine={false} axisLine={{ stroke: '#e2e8f0' }} />
                <RechartsTooltip content={<CustomAnalyticsTooltip />} />
                <Bar dataKey="traditional_days" fill="#94a3b8" name="Legacy Portals" radius={[2, 2, 0, 0]} />
                <Bar dataKey="scholarsetu_days" fill="#1e3a8a" name="ScholarSetu Mesh" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Pathway Retention Area Chart */}
        <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-2xs space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-slate-900">Class 10 to Post-Matric Transition %</h2>
              <p className="text-xs text-slate-500">Mitigating the secondary school tribal dropout rate</p>
            </div>
            <span className="text-xs font-semibold bg-emerald-50 text-emerald-800 px-2 py-0.5 rounded border border-emerald-200">
              94.2% Transition
            </span>
          </div>

          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={pathwayRetention} margin={{ top: 10, right: 15, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="retentionArea" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#059669" stopOpacity={0.2} />
                    <stop offset="100%" stopColor="#059669" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis dataKey="year" stroke="#64748b" fontSize={11} tickLine={false} axisLine={{ stroke: '#e2e8f0' }} />
                <YAxis stroke="#64748b" fontSize={11} unit="%" domain={[0, 100]} tickLine={false} axisLine={{ stroke: '#e2e8f0' }} />
                <RechartsTooltip content={<CustomAnalyticsTooltip />} />
                <Area 
                  type="monotone" 
                  dataKey="with_setu" 
                  stroke="#059669" 
                  strokeWidth={2.5} 
                  fillOpacity={1} 
                  fill="url(#retentionArea)" 
                  name="With ScholarSetu (%)" 
                />
                <Area 
                  type="monotone" 
                  dataKey="without_setu" 
                  stroke="#94a3b8" 
                  strokeWidth={1.5} 
                  strokeDasharray="4 4" 
                  fillOpacity={0} 
                  name="Without Pathway Nudge (%)" 
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
