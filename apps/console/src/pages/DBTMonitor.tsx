import React, { useState } from 'react';
import { 
  CreditCard, ShieldAlert, CheckCircle2, AlertTriangle, 
  Send, RefreshCw, Building2, PhoneCall, HelpCircle, ArrowUpRight 
} from 'lucide-react';
import { PieChart, Pie, Cell, Tooltip as RechartsTooltip, ResponsiveContainer } from 'recharts';

const failureCodes = [
  { name: 'Aadhaar Not Seeded on NPCI', value: 420, color: '#d97706' },
  { name: 'Dormant Bank Account (>12 mos)', value: 280, color: '#dc2626' },
  { name: 'Core Banking Name Discrepancy', value: 160, color: '#1e3a8a' },
  { name: 'Invalid IFSC / Merged Branch', value: 90, color: '#64748b' },
];

interface FailureCase {
  id: string;
  app_id: string;
  student: string;
  district: string;
  bank: string;
  amount: string;
  issue: string;
  severity: 'HIGH' | 'MEDIUM';
  remediation_status: 'DISPATCHED' | 'PENDING' | 'RESOLVED';
}

const mockFailures: FailureCase[] = [
  {
    id: 'f-1',
    app_id: 'APP-2026-JH-8931',
    student: 'Sunita Hansda',
    district: 'Dumka, Jharkhand',
    bank: 'Bank of India (A/C ••••4421)',
    amount: '₹12,000',
    issue: 'Account Dormant (No credit transactions in 14 months)',
    severity: 'HIGH',
    remediation_status: 'DISPATCHED',
  },
  {
    id: 'f-2',
    app_id: 'APP-2026-JH-3891',
    student: 'Birsa Tudu',
    district: 'Khunti, Jharkhand',
    bank: 'State Bank of India (A/C ••••8819)',
    amount: '₹7,000',
    issue: 'Aadhaar Not Seeded on NPCI NACH Mapper',
    severity: 'HIGH',
    remediation_status: 'DISPATCHED',
  },
  {
    id: 'f-3',
    app_id: 'APP-2026-OD-7412',
    student: 'Sukurmani Marandi',
    district: 'Mayurbhanj, Odisha',
    bank: 'Punjab National Bank (A/C ••••1029)',
    amount: '₹15,000',
    issue: 'Core Banking Spelling Variance: MARANDI vs MARNDI',
    severity: 'MEDIUM',
    remediation_status: 'PENDING',
  },
];

export default function DBTMonitor() {
  const [sentNotice, setSentNotice] = useState<string | null>(null);

  const triggerNudge = (student: string) => {
    setSentNotice(`Remediation advisory dispatched via SMS & IVR to ${student} and local Gram Panchayat Mitra.`);
    setTimeout(() => setSentNotice(null), 4000);
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="bg-white rounded-lg border border-slate-200 p-4 shadow-2xs">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
              <span>DBT Sentinel Module</span>
              <span>•</span>
              <span>NPCI NACH & PFMS Pre-Sanction Interception</span>
            </div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight mt-0.5">
              Direct Benefit Transfer (DBT) Failure Sentinel
            </h1>
            <p className="text-xs text-slate-600 mt-0.5">
              Proactively identifies bank account dormancy and unseeded Aadhaar mappings before release, eliminating failed transactions.
            </p>
          </div>
        </div>
      </div>

      {sentNotice && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-900 px-4 py-3 rounded-lg flex items-center gap-2 text-xs font-semibold shadow-2xs">
          <CheckCircle2 className="w-4 h-4 text-emerald-700 shrink-0" />
          <span>{sentNotice}</span>
        </div>
      )}

      {/* KPI Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-2xs">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Pre-Checked Accounts</span>
          <div className="text-xl sm:text-2xl font-bold text-slate-900 mt-1 font-mono">13,670</div>
          <span className="text-[11px] text-slate-500">100% Pre-Sanction Inspected</span>
        </div>
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-2xs">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Failures Prevented</span>
          <div className="text-xl sm:text-2xl font-bold text-emerald-700 mt-1 font-mono">950</div>
          <span className="text-[11px] text-emerald-700 font-semibold">₹1.14 Cr Saved from Rejection</span>
        </div>
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-2xs">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Remediation Rate</span>
          <div className="text-xl sm:text-2xl font-bold text-blue-900 mt-1 font-mono">84.2%</div>
          <span className="text-[11px] text-slate-500">Resolved within 7 Days</span>
        </div>
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-2xs">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Active Interventions</span>
          <div className="text-xl sm:text-2xl font-bold text-amber-700 mt-1 font-mono">150</div>
          <span className="text-[11px] text-amber-700 font-semibold">Mitra Outreach Underway</span>
        </div>
      </div>

      {/* Charts & Failure Diagnosis */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-2xs">
          <h2 className="text-sm font-bold text-slate-900 mb-0.5">Root Cause Classification</h2>
          <p className="text-xs text-slate-500 mb-4">Interception breakdown reported by NPCI Gateway</p>
          <div className="h-60">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={failureCodes} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={3} dataKey="value">
                  {failureCodes.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <RechartsTooltip contentStyle={{ borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '11px' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs pt-3 border-t border-slate-100">
            {failureCodes.map((item) => (
              <div key={item.name} className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-xs shrink-0" style={{ backgroundColor: item.color }} />
                <span className="text-slate-600 truncate text-[11px]">{item.name}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Live Interventions List */}
        <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-2xs space-y-3">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h2 className="text-sm font-bold text-slate-900">Pre-Sanction Banking Advisories</h2>
              <p className="text-xs text-slate-500">Accounts flagged prior to PFMS payment generation</p>
            </div>
            <span className="text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-200 px-2.5 py-0.5 rounded">
              3 Cases Pending
            </span>
          </div>

          <div className="space-y-2.5">
            {mockFailures.map((item) => (
              <div 
                key={item.id}
                className="p-3 rounded border border-slate-200 bg-slate-50 space-y-1.5"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <span className="text-sm font-bold text-slate-900 block">{item.student}</span>
                    <span className="text-[11px] text-slate-500 font-mono">{item.app_id} • {item.district}</span>
                  </div>
                  <span className="text-xs font-bold text-slate-900 bg-white px-2 py-0.5 rounded border border-slate-200 font-mono">
                    {item.amount}
                  </span>
                </div>

                <div className="flex items-center gap-1.5 text-xs">
                  <AlertTriangle className="w-3.5 h-3.5 text-rose-700 shrink-0" />
                  <span className="font-semibold text-rose-800">{item.issue}</span>
                </div>

                <div className="flex items-center justify-between pt-1.5 border-t border-slate-200/80 text-[11px]">
                  <span className="text-slate-500 font-mono">{item.bank}</span>
                  <button
                    onClick={() => triggerNudge(item.student)}
                    className="inline-flex items-center gap-1 text-blue-900 font-bold hover:underline"
                  >
                    <Send className="w-3 h-3" />
                    <span>Dispatch SMS Advisory</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
