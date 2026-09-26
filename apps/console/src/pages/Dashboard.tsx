import React from 'react';
import StatCard from '../components/StatCard';
import { 
  Users, FileText, CheckCircle, AlertTriangle, ShieldCheck, 
  Building2, Clock, Download, Filter, ArrowUpRight
} from 'lucide-react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, 
  ResponsiveContainer, PieChart, Pie, Cell 
} from 'recharts';

const schemeData = [
  { name: 'Pre-Matric ST', count: 4200, amount: '₹2.94 Cr' },
  { name: 'Post-Matric ST', count: 3450, amount: '₹5.00 Cr' },
  { name: 'Top Class ST', count: 1850, amount: '₹4.62 Cr' },
  { name: 'National Fellowship (NFST)', count: 2380, amount: '₹4.28 Cr' },
  { name: 'Overseas Scheme (NOS)', count: 1790, amount: '₹1.58 Cr' },
];

const stateData = [
  { name: 'Submitted / e-KYC', value: 340, color: '#475569' },
  { name: 'Institute Verified', value: 410, color: '#1e3a8a' },
  { name: 'Nodal Officer Approved', value: 290, color: '#0284c7' },
  { name: 'Disbursed (PFMS)', value: 160, color: '#059669' },
];

// Clean Institutional Tooltip (Light, High-Legibility)
const CustomBarTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-white text-slate-800 p-2.5 rounded border border-slate-200 shadow-sm text-xs space-y-0.5">
        <p className="font-bold text-slate-900">{label}</p>
        <p className="text-slate-600">
          Enrolments: <strong className="text-slate-900">{data.count.toLocaleString()}</strong>
        </p>
        <p className="text-slate-500 text-[11px]">
          Disbursement Pool: <span className="font-semibold text-emerald-700">{data.amount}</span>
        </p>
      </div>
    );
  }
  return null;
};

const CustomDonutTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0];
    return (
      <div className="bg-white text-slate-800 p-2.5 rounded border border-slate-200 shadow-sm text-xs space-y-0.5">
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: data.payload.color }} />
          <span className="font-bold text-slate-900">{data.name}</span>
        </div>
        <p className="text-slate-600">
          Count: <strong className="text-slate-900">{data.value.toLocaleString()}</strong> applications
        </p>
      </div>
    );
  }
  return null;
};

export default function Dashboard() {
  const totalPipelineCases = stateData.reduce((acc, curr) => acc + curr.value, 0);

  return (
    <div className="space-y-5">
      {/* Institutional Page Title & Filter Bar */}
      <div className="bg-white rounded-lg border border-slate-200 p-4 shadow-2xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
              <span>Direct Benefit Transfer Cell</span>
              <span>•</span>
              <span>Central Sector & Centrally Sponsored Schemes</span>
            </div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight mt-0.5">
              National Scholarship Monitoring Dashboard
            </h1>
          </div>

          {/* Institutional Controls */}
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <div className="flex items-center gap-1 bg-slate-50 border border-slate-200 rounded px-2.5 py-1.5 text-slate-700 font-medium">
              <Filter className="w-3.5 h-3.5 text-slate-500" />
              <span>AY 2026-27</span>
            </div>

            <div className="flex items-center gap-1 bg-slate-50 border border-slate-200 rounded px-2.5 py-1.5 text-slate-700 font-medium">
              <span>All 36 States & UTs</span>
            </div>

            <button 
              onClick={() => window.print()}
              className="bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 font-semibold px-3 py-1.5 rounded transition flex items-center gap-1.5 shadow-2xs"
            >
              <Download className="w-3.5 h-3.5 text-slate-600" />
              <span>Export Report</span>
            </button>
          </div>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-slate-200 p-4 shadow-2xs">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">
            Total ST Beneficiaries
          </span>
          <div className="flex items-baseline justify-between mt-2">
            <span className="text-2xl font-bold text-slate-900 font-mono">13,670</span>
            <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
              +14.2% YoY
            </span>
          </div>
          <p className="text-[11px] text-slate-500 mt-2">Across 75 PVTG and ST communities</p>
        </div>

        <div className="bg-white rounded-lg border border-slate-200 p-4 shadow-2xs">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">
            DBT Disbursed (PFMS APBS)
          </span>
          <div className="flex items-baseline justify-between mt-2">
            <span className="text-2xl font-bold text-slate-900 font-mono">₹18.42 Cr</span>
            <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
              100% Seeded
            </span>
          </div>
          <p className="text-[11px] text-slate-500 mt-2">Aadhaar payment bridge synchronized</p>
        </div>

        <div className="bg-white rounded-lg border border-slate-200 p-4 shadow-2xs">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">
            Zero-Dormancy Pre-Clearance
          </span>
          <div className="flex items-baseline justify-between mt-2">
            <span className="text-2xl font-bold text-slate-900 font-mono">99.1%</span>
            <span className="text-xs font-semibold text-blue-700 bg-blue-50 px-1.5 py-0.5 rounded border border-blue-200">
              DBT Sentinel
            </span>
          </div>
          <p className="text-[11px] text-slate-500 mt-2">Bank dormancy intercepted pre-sanction</p>
        </div>

        <div className="bg-white rounded-lg border border-slate-200 p-4 shadow-2xs">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">
            Average Verification SLA
          </span>
          <div className="flex items-baseline justify-between mt-2">
            <span className="text-2xl font-bold text-slate-900 font-mono">3.4 Days</span>
            <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
              Within SLA
            </span>
          </div>
          <p className="text-[11px] text-slate-500 mt-2">Statutory maximum threshold: 14 Days</p>
        </div>
      </div>

      {/* Main Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Applications by Scheme */}
        <div className="lg:col-span-2 bg-white rounded-lg border border-slate-200 p-5 shadow-2xs">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-bold text-slate-900">Enrolment by Ministry Scheme</h2>
              <p className="text-xs text-slate-500">Distribution of active scholarship candidates for AY 2026-27</p>
            </div>
            <span className="text-xs font-mono font-medium text-slate-500 bg-slate-50 px-2 py-1 rounded border border-slate-200">
              Total: 13,670
            </span>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={schemeData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis 
                  dataKey="name" 
                  tick={{ fontSize: 11, fill: '#475569' }} 
                  axisLine={{ stroke: '#cbd5e1' }}
                  tickLine={false}
                  interval={0}
                  angle={-10}
                  textAnchor="end"
                />
                <YAxis 
                  tick={{ fontSize: 11, fill: '#475569' }} 
                  axisLine={false} 
                  tickLine={false} 
                />
                <RechartsTooltip content={<CustomBarTooltip />} />
                <Bar 
                  dataKey="count" 
                  fill="#1e3a8a" 
                  radius={[3, 3, 0, 0]} 
                  barSize={36} 
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Verification Pipeline Funnel */}
        <div className="bg-white rounded-lg border border-slate-200 p-5 shadow-2xs flex flex-col justify-between">
          <div>
            <h2 className="text-sm font-bold text-slate-900">Verification & Sanction Funnel</h2>
            <p className="text-xs text-slate-500">Status of active batch under review</p>
          </div>

          <div className="h-48 relative my-2">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={stateData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={75}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {stateData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <RechartsTooltip content={<CustomDonutTooltip />} />
              </PieChart>
            </ResponsiveContainer>

            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              <span className="text-xl font-bold text-slate-900 font-mono">
                {totalPipelineCases.toLocaleString()}
              </span>
              <span className="text-[10px] text-slate-500 font-medium uppercase tracking-wider">
                Active Batch
              </span>
            </div>
          </div>

          {/* Micro Legend */}
          <div className="grid grid-cols-2 gap-2 text-xs pt-3 border-t border-slate-100">
            {stateData.map((item) => (
              <div key={item.name} className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-xs shrink-0" style={{ backgroundColor: item.color }} />
                <span className="text-slate-600 truncate text-[11px]">{item.name}:</span>
                <span className="font-bold text-slate-900 font-mono text-[11px]">{item.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Institutional Operational Integrity Banner */}
      <div className="bg-slate-900 text-white rounded-lg p-4 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
              National Infrastructure Telemetry & Statutory Audit
            </span>
          </div>
          <p className="text-xs text-slate-400">
            DigiLocker, UIDAI e-KYC, UDISE+, and NPCI NACH APBS gateways operating normally.
          </p>
        </div>

        <div className="flex items-center gap-4 text-xs font-mono">
          <div>
            <span className="text-slate-500 block text-[10px] font-sans">Verification Velocity</span>
            <span className="text-emerald-400 font-bold">0.05s / Credential</span>
          </div>
          <div className="border-l border-slate-700 pl-4">
            <span className="text-slate-500 block text-[10px] font-sans">Ledger Cryptography</span>
            <span className="text-slate-200 font-bold">Ed25519 PKCS#8</span>
          </div>
        </div>
      </div>
    </div>
  );
}
