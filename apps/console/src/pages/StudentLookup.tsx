import React, { useState } from 'react';
import { 
  Search, User, GraduationCap, ShieldCheck, QrCode, 
  MapPin, ArrowRight
} from 'lucide-react';
import { Link } from 'react-router-dom';

interface StudentResult {
  id: string;
  name: string;
  devnagari: string;
  apaar_id: string;
  app_id: string;
  tribe: string;
  district: string;
  school: string;
  scheme: string;
  status: string;
  passport_verified: boolean;
}

const mockStudents: StudentResult[] = [
  {
    id: 'stu-sunita-001',
    name: 'Sunita Hansda',
    devnagari: 'सुनीता हांसदा',
    apaar_id: '9921-8842-1029',
    app_id: 'APP-2026-JH-8931',
    tribe: 'Santal Tribe',
    district: 'Dumka, Jharkhand',
    school: 'Dumka Govt Inter College',
    scheme: 'Post-Matric (Class 11 Science)',
    status: 'Inst. Verified • Under Authority Review',
    passport_verified: true,
  },
  {
    id: 'stu-rahul-002',
    name: 'Rahul Hansda',
    devnagari: 'राहुल हांसदा',
    apaar_id: '9921-8842-1030',
    app_id: 'APP-2026-JH-1102',
    tribe: 'Santal Tribe',
    district: 'Dumka, Jharkhand',
    school: 'Govt High School Dumka',
    scheme: 'Pre-Matric (Class 9)',
    status: 'Disbursed (₹7,000 Credited)',
    passport_verified: true,
  },
  {
    id: 'stu-sukurmani-003',
    name: 'Sukurmani Marandi',
    devnagari: 'सुकुरमनी मरांडी',
    apaar_id: '8830-1928-4412',
    app_id: 'APP-2026-OD-7412',
    tribe: 'Santhal Tribe',
    district: 'Mayurbhanj, Odisha',
    school: 'Baripada Higher Secondary School',
    scheme: 'National Overseas Scholarship (NOS)',
    status: 'Review Queue • Caste Verified',
    passport_verified: true,
  },
  {
    id: 'stu-birsa-004',
    name: 'Birsa Tudu',
    devnagari: 'बिरसा टुडू',
    apaar_id: '7721-3940-8812',
    app_id: 'APP-2026-JH-3891',
    tribe: 'Munda Tribe',
    district: 'Khunti, Jharkhand',
    school: 'Birsa Munda Ashram School Khunti',
    scheme: 'Top Class Education for ST',
    status: 'DBT Remediation Pending',
    passport_verified: false,
  },
];

export default function StudentLookup() {
  const [query, setQuery] = useState('');

  const filtered = query.trim().length > 0 
    ? mockStudents.filter((s) => 
        s.name.toLowerCase().includes(query.toLowerCase()) ||
        s.devnagari.includes(query) ||
        s.apaar_id.includes(query) ||
        s.app_id.toLowerCase().includes(query.toLowerCase()) ||
        s.district.toLowerCase().includes(query.toLowerCase())
      )
    : mockStudents;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="bg-white rounded-lg border border-slate-200 p-4 shadow-2xs">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
              <span>National Beneficiary Registry</span>
              <span>•</span>
              <span>APAAR & Digilocker Search</span>
            </div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight mt-0.5">
              Beneficiary & Student Directory
            </h1>
            <p className="text-xs text-slate-600 mt-0.5">
              Lookup ST scholarship recipients by APAAR ID, Pen ID, Application Number, or Name across all Central & State schemes.
            </p>
          </div>
        </div>
      </div>

      {/* Search Bar */}
      <div className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-2xs space-y-2.5">
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by Name (e.g. 'Sunita'), APAAR ID, Application ID, or District..."
            className="w-full pl-9 pr-3 py-2 text-xs sm:text-sm bg-slate-50 border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-slate-700 font-medium"
          />
        </div>

        {/* Quick Suggestion Chips */}
        <div className="flex flex-wrap items-center gap-1.5 pt-1 text-xs">
          <span className="text-slate-400 font-medium">Quick Searches:</span>
          {['Sunita Hansda', 'Rahul Hansda', 'Sukurmani Marandi', 'Birsa Tudu'].map((name) => (
            <button
              key={name}
              onClick={() => setQuery(name)}
              className="px-2 py-0.5 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium text-[11px] transition"
            >
              {name}
            </button>
          ))}
          {query && (
            <button
              onClick={() => setQuery('')}
              className="text-xs text-rose-700 hover:underline font-semibold ml-auto"
            >
              Clear Search
            </button>
          )}
        </div>
      </div>

      {/* Results Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
        {filtered.map((s) => (
          <div
            key={s.id}
            className="bg-white rounded-lg border border-slate-200 p-4 shadow-2xs space-y-3 hover:border-slate-300 transition"
          >
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-bold text-base text-slate-900 leading-tight">
                    {s.name}
                  </h3>
                  <span className="text-xs text-slate-500 font-medium font-hindi">
                    ({s.devnagari})
                  </span>
                </div>
                <div className="flex items-center gap-1.5 text-xs text-slate-500 mt-0.5">
                  <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  <span>{s.district}</span>
                  <span>•</span>
                  <span className="font-medium text-slate-700">{s.tribe}</span>
                </div>
              </div>

              {s.passport_verified && (
                <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded border border-emerald-200 bg-emerald-50 text-emerald-800 shrink-0">
                  <ShieldCheck className="w-3 h-3 text-emerald-700" />
                  Passport Valid
                </span>
              )}
            </div>

            {/* School & Scheme */}
            <div className="p-2.5 rounded bg-slate-50 border border-slate-200 text-xs space-y-1">
              <div className="flex items-center justify-between text-slate-700">
                <span className="text-slate-500">Institution:</span>
                <span className="font-medium text-slate-900 text-right">{s.school}</span>
              </div>
              <div className="flex items-center justify-between text-slate-700">
                <span className="text-slate-500">Scheme:</span>
                <span className="font-medium text-slate-900 text-right">{s.scheme}</span>
              </div>
            </div>

            {/* Identifier Badges */}
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs pt-2 border-t border-slate-100">
              <div className="space-x-2 font-mono text-[11px] text-slate-500">
                <span>APP: <strong className="text-blue-900">{s.app_id}</strong></span>
                <span>•</span>
                <span>APAAR: <strong className="text-slate-800">{s.apaar_id}</strong></span>
              </div>

              <Link
                to={`/application/${s.app_id}`}
                className="text-xs font-bold text-blue-900 hover:underline inline-flex items-center gap-1"
              >
                <span>View Full Record</span>
                <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
