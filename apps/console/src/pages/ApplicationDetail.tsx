import { useParams, Link } from 'react-router-dom';
import StatusBadge from '../components/StatusBadge';
import TimelineView from '../components/TimelineView';
import { CanonicalState, SchemeType } from '../types';
import { ArrowLeft, Building2, MapPin, Users, Award, ShieldCheck, FileCheck, CheckCircle2 } from 'lucide-react';

const mockApp = {
  id: 'APP-2026-JH-8931',
  student_name: 'Sunita Hansda (सुनीता हांसदा)',
  scheme: SchemeType.POST_MATRIC,
  canonical_state: CanonicalState.INSTITUTE_VERIFICATION,
  district: 'Dumka, Jharkhand',
  tribe: 'Santal Tribe (PVTG Scheduled)',
  institution: 'Dumka Government Inter College, Dumka',
  apaar_id: 'APAAR-8839-2026-9011',
  sanction_amount: '₹14,500',
  dbt_status: 'Pre-Clearance Passed (NPCI Seeded)',
  ed25519_sig: 'ed25519:6a7b8c9d0e1f3a2b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f'
};

const mockEvents = [
  {
    event_id: 'e4',
    event_type: 'INDIC_IDENTITY_MATCH',
    occurred_at: '2026-04-12T10:30:00Z',
    actor: 'Indic Identity Resolver',
    description: "Phonetic similarity 94.2% on 'Hansda' vs 'Hasdak'. Approved by Nodal Officer.",
    details: {}
  },
  {
    event_id: 'e3',
    event_type: 'VERIFICATION',
    occurred_at: '2026-04-10T10:00:00Z',
    actor: 'Principal (Dumka Govt College)',
    description: 'Verified Class 11 Science enrolment & hostel residency.',
    details: {}
  },
  {
    event_id: 'e2',
    event_type: 'PASSPORT_ATTESTATION_REUSE',
    occurred_at: '2026-04-02T14:30:00Z',
    actor: 'Verification Mesh',
    description: 'ST Caste Certificate attestation #ATT-ST-9912 reused with valid Ed25519 digital signature.',
    details: {}
  },
  {
    event_id: 'e1',
    event_type: 'PATHWAY_NUDGE_CLAIM',
    occurred_at: '2026-04-01T09:15:00Z',
    actor: 'Somu Munda (Father / Family Mode)',
    description: 'Claimed prefilled Post-Matric application triggered by Class 10 Matriculation result in DigiLocker.',
    details: {}
  }
];

export default function ApplicationDetail() {
  const { id } = useParams();

  return (
    <div className="space-y-6">
      {/* Back Link */}
      <Link 
        to="/review-queue"
        className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-500 hover:text-indigo-600 transition"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>Back to Review Queue</span>
      </Link>

      {/* Main Student Header Card */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1 text-xs">
              <span className="font-mono bg-indigo-50 text-indigo-700 font-bold px-2 py-0.5 rounded-md border border-indigo-200">
                {id || mockApp.id}
              </span>
              <span className="text-slate-400">•</span>
              <span className="text-slate-500 font-medium">{mockApp.scheme}</span>
            </div>
            <h1 className="text-2xl font-black text-slate-900 tracking-tight">{mockApp.student_name}</h1>
          </div>
          <div className="flex items-center gap-2 self-start sm:self-auto">
            <StatusBadge status={mockApp.canonical_state} />
          </div>
        </div>

        {/* Quick Highlights Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mt-6 pt-5 border-t border-slate-100 text-xs">
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/70">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">District & State</span>
            <div className="flex items-center gap-1.5 mt-1 font-bold text-slate-800">
              <MapPin className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
              <span>{mockApp.district}</span>
            </div>
          </div>

          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/70">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">Tribal Community</span>
            <div className="flex items-center gap-1.5 mt-1 font-bold text-slate-800">
              <Users className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
              <span>{mockApp.tribe}</span>
            </div>
          </div>

          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/70">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">Sanctioned Amount</span>
            <div className="flex items-center gap-1.5 mt-1 font-black text-emerald-700 text-sm">
              <Award className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              <span>{mockApp.sanction_amount}</span>
            </div>
          </div>

          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/70">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">DBT Pre-Clearance</span>
            <div className="flex items-center gap-1.5 mt-1 font-bold text-emerald-700 truncate">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              <span className="truncate">Active NPCI Mapper</span>
            </div>
          </div>
        </div>

        {/* Institution Details */}
        <div className="mt-3 p-3 bg-indigo-50/50 rounded-xl border border-indigo-100 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <Building2 className="w-4 h-4 text-indigo-600 shrink-0" />
            <span className="font-semibold text-slate-800">{mockApp.institution}</span>
          </div>
          <span className="text-[10px] font-mono text-indigo-700 bg-white px-2 py-0.5 rounded border border-indigo-200">
            AISHE Verified
          </span>
        </div>
      </div>

      {/* Application Timeline Card */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="text-base font-bold text-slate-900">Cryptographic Audit Trail (Canonical Ledger)</h2>
            <p className="text-xs text-slate-500">Every state transition is immutable, timestamped and Ed25519 signed.</p>
          </div>
          <span className="text-xs font-mono bg-emerald-50 text-emerald-800 font-bold px-2.5 py-1 rounded-lg border border-emerald-200 flex items-center gap-1">
            <FileCheck className="w-3.5 h-3.5 text-emerald-600" /> Tamper-Proof
          </span>
        </div>
        <TimelineView events={mockEvents} />
      </div>
    </div>
  );
}
