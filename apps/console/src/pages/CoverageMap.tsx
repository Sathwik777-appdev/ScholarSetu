import React, { useState } from 'react';
import { MapPin, ShieldCheck, Users, AlertCircle, ArrowUpRight, Search, Filter } from 'lucide-react';

interface CoverageData {
  state: string;
  district: string;
  pvtg_tribes: string;
  total_enrolled: number;
  total_scholarship: number;
  coverage_pct: number;
  pvtg_coverage_pct: number;
  unreached_count: number;
}

const mockCoverage: CoverageData[] = [
  { 
    state: 'Jharkhand', 
    district: 'Dumka', 
    pvtg_tribes: 'Santal, Mal Paharia', 
    total_enrolled: 14200, 
    total_scholarship: 11650, 
    coverage_pct: 82.0, 
    pvtg_coverage_pct: 68.4,
    unreached_count: 2550
  },
  { 
    state: 'Jharkhand', 
    district: 'Khunti', 
    pvtg_tribes: 'Munda, Birhor (PVTG)', 
    total_enrolled: 9800, 
    total_scholarship: 7450, 
    coverage_pct: 76.0, 
    pvtg_coverage_pct: 54.2,
    unreached_count: 2350
  },
  { 
    state: 'Odisha', 
    district: 'Mayurbhanj', 
    pvtg_tribes: 'Santhal, Kolha, Hill Kharia', 
    total_enrolled: 16500, 
    total_scholarship: 12200, 
    coverage_pct: 73.9, 
    pvtg_coverage_pct: 61.0,
    unreached_count: 4300
  },
  { 
    state: 'Maharashtra', 
    district: 'Nandurbar', 
    pvtg_tribes: 'Bhil, Pawara, Katkari (PVTG)', 
    total_enrolled: 12000, 
    total_scholarship: 4500, 
    coverage_pct: 37.5, 
    pvtg_coverage_pct: 20.1,
    unreached_count: 7500
  },
  { 
    state: 'Madhya Pradesh', 
    district: 'Jhabua', 
    pvtg_tribes: 'Bhil, Bhilala', 
    total_enrolled: 21000, 
    total_scholarship: 6100, 
    coverage_pct: 29.0, 
    pvtg_coverage_pct: 16.5,
    unreached_count: 14900
  },
  { 
    state: 'Chhattisgarh', 
    district: 'Bastar', 
    pvtg_tribes: 'Gond, Maria, Muria, Halba', 
    total_enrolled: 18400, 
    total_scholarship: 11400, 
    coverage_pct: 62.0, 
    pvtg_coverage_pct: 44.8,
    unreached_count: 7000
  },
];

export default function CoverageMap() {
  const [filterQuery, setFilterQuery] = useState('');
  const [selectedState, setSelectedState] = useState('ALL');

  const filtered = mockCoverage.filter((item) => {
    const matchesSearch = 
      item.district.toLowerCase().includes(filterQuery.toLowerCase()) ||
      item.state.toLowerCase().includes(filterQuery.toLowerCase()) ||
      item.pvtg_tribes.toLowerCase().includes(filterQuery.toLowerCase());
    const matchesState = selectedState === 'ALL' || item.state === selectedState;
    return matchesSearch && matchesState;
  });

  const getBadgeStyle = (pct: number) => {
    if (pct >= 70) return 'bg-emerald-50 text-emerald-800 border-emerald-200';
    if (pct >= 50) return 'bg-amber-50 text-amber-800 border-amber-200';
    return 'bg-rose-50 text-rose-800 border-rose-200';
  };

  const getProgressBarColor = (pct: number) => {
    if (pct >= 70) return 'bg-emerald-600';
    if (pct >= 50) return 'bg-amber-500';
    return 'bg-rose-600';
  };

  return (
    <div className="space-y-5">
      {/* Header with National Security & DPDP badge */}
      <div className="bg-white rounded-lg border border-slate-200 p-4 shadow-2xs">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
              <span>Reach Radar Protocol</span>
              <span>•</span>
              <span>DPDP Act 2023 Compliant (PPRL Cross-Linkage)</span>
            </div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight mt-0.5">
              Scheduled Areas Coverage & Saturation Matrix
            </h1>
            <p className="text-xs text-slate-600 mt-0.5">
              Privacy-Preserving Record Linkage cross-matching UDISE+ school enrolment registers with MoTA scholarship records.
            </p>
          </div>
        </div>
      </div>

      {/* Metric Tiles */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-2xs">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Total ST Enrolled</span>
          <div className="text-xl sm:text-2xl font-bold text-slate-900 mt-1 font-mono">91,900</div>
          <span className="text-[11px] text-slate-500">UDISE+ Academic Registers</span>
        </div>
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-2xs">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Scholarships Active</span>
          <div className="text-xl sm:text-2xl font-bold text-slate-900 mt-1 font-mono">53,300</div>
          <span className="text-[11px] text-slate-500">Central & State Portals</span>
        </div>
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-2xs">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Avg Saturation</span>
          <div className="text-xl sm:text-2xl font-bold text-blue-900 mt-1 font-mono">58.0%</div>
          <span className="text-[11px] text-emerald-700 font-semibold">+6.4% YoY Growth</span>
        </div>
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-2xs">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Unreached Gap</span>
          <div className="text-xl sm:text-2xl font-bold text-rose-700 mt-1 font-mono">38,600</div>
          <span className="text-[11px] text-rose-600 font-semibold">Priority Out-Reach</span>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-3 rounded-lg border border-slate-200 shadow-2xs flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-80">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={filterQuery}
            onChange={(e) => setFilterQuery(e.target.value)}
            placeholder="Search district, tribe, or state..."
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-slate-700 font-medium"
          />
        </div>

        <div className="flex items-center gap-1.5 self-start sm:self-auto overflow-x-auto w-full sm:w-auto pb-1 sm:pb-0">
          <span className="text-xs text-slate-500 font-medium whitespace-nowrap mr-1">State:</span>
          {['ALL', 'Jharkhand', 'Odisha', 'Maharashtra', 'Madhya Pradesh', 'Chhattisgarh'].map((st) => (
            <button
              key={st}
              onClick={() => setSelectedState(st)}
              className={`px-2.5 py-1 text-xs rounded font-semibold transition whitespace-nowrap border ${
                selectedState === st
                  ? 'bg-blue-900 text-white border-blue-900 shadow-2xs'
                  : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* MOBILE CARDS VIEW (< 768px) */}
      <div className="grid grid-cols-1 gap-3 md:hidden">
        {filtered.map((row, idx) => (
          <div key={idx} className="bg-white p-4 rounded-lg border border-slate-200 shadow-2xs space-y-3">
            {/* Header: District, State, and Saturation Pill */}
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="flex items-center gap-1.5">
                  <MapPin className="w-3.5 h-3.5 text-blue-900 shrink-0" />
                  <span className="text-base font-bold text-slate-900 leading-tight">{row.district}</span>
                </div>
                <span className="text-xs text-slate-500 font-medium ml-5">{row.state}</span>
              </div>
              <span className={`text-xs font-bold px-2 py-0.5 rounded border ${getBadgeStyle(row.coverage_pct)}`}>
                {row.coverage_pct}% Covered
              </span>
            </div>

            {/* Tribal Demographics */}
            <div className="bg-slate-50 px-2.5 py-1.5 rounded border border-slate-200 text-xs text-slate-700">
              <span className="font-semibold text-slate-500">Target Tribes:</span> {row.pvtg_tribes}
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-3 gap-2 pt-1 border-t border-slate-100 text-center font-mono">
              <div>
                <span className="text-[10px] uppercase font-bold text-slate-400 block font-sans">Enrolled</span>
                <span className="text-sm font-bold text-slate-800">{row.total_enrolled.toLocaleString()}</span>
              </div>
              <div>
                <span className="text-[10px] uppercase font-bold text-slate-400 block font-sans">Scholarships</span>
                <span className="text-sm font-bold text-emerald-700">{row.total_scholarship.toLocaleString()}</span>
              </div>
              <div>
                <span className="text-[10px] uppercase font-bold text-slate-400 block font-sans">Unreached</span>
                <span className="text-sm font-bold text-rose-700">{row.unreached_count.toLocaleString()}</span>
              </div>
            </div>

            {/* Visual Progress Bar */}
            <div className="space-y-1 pt-1">
              <div className="flex justify-between text-[11px] font-semibold text-slate-600">
                <span>Overall Saturation</span>
                <span className="text-slate-800 font-bold">{row.coverage_pct}%</span>
              </div>
              <div className="w-full bg-slate-100 h-2 rounded overflow-hidden">
                <div 
                  className={`h-full ${getProgressBarColor(row.coverage_pct)}`} 
                  style={{ width: `${row.coverage_pct}%` }} 
                />
              </div>
            </div>

            {/* PVTG Coverage Row */}
            <div className="flex items-center justify-between text-xs pt-1 border-t border-slate-100 text-slate-600">
              <span className="font-medium">PVTG Saturation:</span>
              <span className={`font-bold px-2 py-0.5 rounded border text-[11px] ${getBadgeStyle(row.pvtg_coverage_pct)}`}>
                {row.pvtg_coverage_pct}%
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* DESKTOP TABLE VIEW (>= 768px) */}
      <div className="hidden md:block bg-white rounded-lg border border-slate-200 shadow-2xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50 text-[11px] font-bold uppercase tracking-wider text-slate-500">
              <tr>
                <th scope="col" className="px-4 py-3 text-left">District & State</th>
                <th scope="col" className="px-4 py-3 text-left">Target Tribal Communities</th>
                <th scope="col" className="px-4 py-3 text-right">ST Enrolled (UDISE+)</th>
                <th scope="col" className="px-4 py-3 text-right">Active Beneficiaries</th>
                <th scope="col" className="px-4 py-3 text-center">Saturation Ratio</th>
                <th scope="col" className="px-4 py-3 text-center">PVTG Coverage</th>
                <th scope="col" className="px-4 py-3 text-right">Unreached Gap</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs font-medium text-slate-700">
              {filtered.map((row, idx) => (
                <tr key={idx} className="hover:bg-slate-50 transition-colors">
                  <td className="px-4 py-3.5 whitespace-nowrap">
                    <div className="font-bold text-slate-900 text-sm">{row.district}</div>
                    <div className="text-[11px] text-slate-500">{row.state}</div>
                  </td>
                  <td className="px-4 py-3.5 max-w-xs truncate text-slate-600 font-normal">
                    {row.pvtg_tribes}
                  </td>
                  <td className="px-4 py-3.5 whitespace-nowrap text-right font-mono font-semibold text-slate-800">
                    {row.total_enrolled.toLocaleString()}
                  </td>
                  <td className="px-4 py-3.5 whitespace-nowrap text-right font-mono font-semibold text-emerald-700">
                    {row.total_scholarship.toLocaleString()}
                  </td>
                  <td className="px-4 py-3.5 whitespace-nowrap text-center">
                    <div className="inline-flex items-center gap-2">
                      <div className="w-16 bg-slate-100 h-1.5 rounded overflow-hidden">
                        <div 
                          className={`h-full ${getProgressBarColor(row.coverage_pct)}`} 
                          style={{ width: `${row.coverage_pct}%` }} 
                        />
                      </div>
                      <span className={`px-2 py-0.5 rounded text-[11px] font-bold border ${getBadgeStyle(row.coverage_pct)}`}>
                        {row.coverage_pct}%
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3.5 whitespace-nowrap text-center">
                    <span className={`px-2 py-0.5 rounded text-[11px] font-bold border ${getBadgeStyle(row.pvtg_coverage_pct)}`}>
                      {row.pvtg_coverage_pct}%
                    </span>
                  </td>
                  <td className="px-4 py-3.5 whitespace-nowrap text-right font-mono font-bold text-rose-700">
                    {row.unreached_count.toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
