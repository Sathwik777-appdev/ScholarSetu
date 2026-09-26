import React, { useState } from 'react';
import { 
  CheckCircle2, XCircle, AlertCircle, Clock, FileCheck2, 
  ChevronDown, ChevronUp, UserCheck, Search, Filter, ShieldCheck, 
  ExternalLink
} from 'lucide-react';
import { Link } from 'react-router-dom';

interface ReviewCase {
  id: string;
  application_id: string;
  student_name: string;
  state: string;
  scheme: string;
  reason: string;
  claim_type: string;
  explanation: string;
  indic_comparison?: {
    source_a: string;
    source_b: string;
    similarity: string;
    devnagari: string;
  };
  evidence_type: string;
  sla_deadline: string;
  days_remaining: number;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
}

const initialCases: ReviewCase[] = [
  {
    id: 'case-001',
    application_id: 'APP-2026-JH-8931',
    student_name: 'Sunita Hansda (सुनीता हांसदा)',
    state: 'Dumka, Jharkhand',
    scheme: 'Post-Matric (Class 11 Science)',
    reason: 'Indic Name Transliteration',
    claim_type: 'Phonetic Suffix Variance',
    explanation: "Aadhaar UIDAI record reads 'Sunita Hansda' while Class 10 school register reads 'Sunita Hansdah'. Devanagari transliteration 'सुनीता हांसदा' matches 100%. Father's name ('Babulal Hansda') and DOB ('12-Apr-2008') are identical.",
    indic_comparison: {
      source_a: 'Sunita Hansda (Aadhaar UIDAI)',
      source_b: 'Sunita Hansdah (UDISE+ School)',
      similarity: '94.2% (Double Metaphone Match)',
      devnagari: 'सुनीता हांसदा (e-District Verified)',
    },
    evidence_type: 'Ed25519 Signed Marksheet & Aadhaar Hash',
    sla_deadline: '24 Hours',
    days_remaining: 1,
    status: 'PENDING',
  },
  {
    id: 'case-002',
    application_id: 'APP-2026-OD-7412',
    student_name: 'Sukurmani Marandi',
    state: 'Mayurbhanj, Odisha',
    scheme: 'National Overseas Scholarship (NOS)',
    reason: 'Caste Certificate Attestation Reuse',
    claim_type: 'ST Verification Mesh Reuse',
    explanation: 'ST Certificate verified in 2024 for Post-Matric. Ed25519 digital signature valid with lifetime policy. No re-verification with local Tehsildar required.',
    evidence_type: 'Scholarship Passport Attestation #ATT-ST-9912',
    sla_deadline: '48 Hours',
    days_remaining: 2,
    status: 'PENDING',
  },
  {
    id: 'case-003',
    application_id: 'APP-2026-JH-3891',
    student_name: 'Birsa Tudu',
    state: 'Khunti, Jharkhand',
    scheme: 'Top Class Education for ST',
    reason: 'DBT Guardian Warning',
    claim_type: 'Dormant Bank Account Catch',
    explanation: "NPCI Aadhaar Mapper reports Bank of India account inactive for 14 months. Pre-sanction check halted payout. Local CSC Mitra alerted to collect ₹50 deposit to activate.",
    evidence_type: 'NPCI Pre-Sanction Health Report (Mock Gateway)',
    sla_deadline: '3 Days',
    days_remaining: 3,
    status: 'PENDING',
  },
  {
    id: 'case-004',
    application_id: 'APP-2026-MH-5520',
    student_name: 'Anjali Pawara',
    state: 'Nandurbar, Maharashtra',
    scheme: 'Pre-Matric ST Scholarship',
    reason: 'AISHE Enrolment Verification',
    claim_type: 'Ashram School Roster Corroboration',
    explanation: 'Institutional Headmaster verified physical attendance via Mitra Assisted Mode with time-boxed student OTP consent.',
    evidence_type: 'DEPA Time-Boxed Consent #CON-8841',
    sla_deadline: '5 Days',
    days_remaining: 5,
    status: 'PENDING',
  },
];

export default function ReviewQueue() {
  const [cases, setCases] = useState<ReviewCase[]>(initialCases);
  const [expandedId, setExpandedId] = useState<string | null>('case-001');
  const [filterQuery, setFilterQuery] = useState('');
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  const handleDecision = (id: string, decision: 'APPROVED' | 'REJECTED') => {
    setCases((prev) =>
      prev.map((c) => (c.id === id ? { ...c, status: decision } : c))
    );
    const targetCase = cases.find((c) => c.id === id);
    setActionNotice(
      `Application ${targetCase?.application_id} marked as ${decision}. Audit record committed to ledger.`
    );
    setTimeout(() => setActionNotice(null), 4000);
  };

  const filteredCases = cases.filter((c) =>
    c.student_name.toLowerCase().includes(filterQuery.toLowerCase()) ||
    c.application_id.toLowerCase().includes(filterQuery.toLowerCase()) ||
    c.reason.toLowerCase().includes(filterQuery.toLowerCase())
  );

  return (
    <div className="space-y-5">
      {/* Executive Header */}
      <div className="bg-white rounded-lg border border-slate-200 p-4 shadow-2xs">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
              <span>Nodal Exception Processing</span>
              <span>•</span>
              <span>Statutory Human-in-the-Loop Review</span>
            </div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight mt-0.5">
              Nodal Officer Verification Queue
            </h1>
            <p className="text-xs text-slate-600 mt-0.5">
              Indic phonetic variances, attestation reuse validations, and pre-sanction exceptions requiring administrative sign-off.
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <span className="bg-rose-50 text-rose-700 px-2.5 py-1 rounded border border-rose-200 font-semibold">
              1 SLA Urgent (24h)
            </span>
            <span className="bg-slate-100 text-slate-700 px-2.5 py-1 rounded border border-slate-200 font-semibold">
              {cases.filter((c) => c.status === 'PENDING').length} Pending Review
            </span>
          </div>
        </div>
      </div>

      {/* Action Notification Toast */}
      {actionNotice && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-900 px-4 py-3 rounded-lg flex items-center gap-2 text-xs font-semibold shadow-2xs">
          <CheckCircle2 className="w-4 h-4 text-emerald-700 shrink-0" />
          <span>{actionNotice}</span>
        </div>
      )}

      {/* Search Bar */}
      <div className="bg-white p-3 rounded-lg border border-slate-200 shadow-2xs flex items-center justify-between gap-3">
        <div className="relative w-full sm:w-96">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={filterQuery}
            onChange={(e) => setFilterQuery(e.target.value)}
            placeholder="Search candidate name, Application ID, or anomaly type..."
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-slate-700 font-medium"
          />
        </div>

        <span className="hidden sm:inline text-xs text-slate-500 font-medium">
          Showing {filteredCases.length} of {cases.length} records
        </span>
      </div>

      {/* MOBILE CARDS VIEW (< 768px) */}
      <div className="grid grid-cols-1 gap-3 md:hidden">
        {filteredCases.map((c) => (
          <div 
            key={c.id} 
            className={`bg-white rounded-lg border p-4 shadow-2xs space-y-3 ${
              c.status === 'APPROVED' ? 'border-emerald-200 bg-emerald-50/20' :
              c.status === 'REJECTED' ? 'border-rose-200 bg-rose-50/20' :
              'border-slate-200'
            }`}
          >
            {/* Top Row: App ID, Student Name, SLA Timer */}
            <div className="flex items-start justify-between gap-2">
              <div>
                <span className="text-[11px] font-mono font-bold text-blue-900 block">
                  {c.application_id}
                </span>
                <span className="text-base font-bold text-slate-900 leading-tight block">
                  {c.student_name}
                </span>
                <span className="text-[11px] text-slate-500">{c.state}</span>
              </div>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded border whitespace-nowrap ${
                c.days_remaining <= 1 ? 'bg-rose-50 text-rose-700 border-rose-200' :
                c.days_remaining <= 3 ? 'bg-amber-50 text-amber-700 border-amber-200' :
                'bg-slate-50 text-slate-600 border-slate-200'
              }`}>
                {c.days_remaining}d SLA Left
              </span>
            </div>

            {/* Scheme & Reason Pill */}
            <div className="flex flex-wrap items-center gap-1.5 text-xs">
              <span className="bg-slate-100 text-slate-700 font-medium px-2 py-0.5 rounded border border-slate-200 text-[11px]">
                {c.scheme}
              </span>
              <span className="bg-amber-50 text-amber-900 font-semibold px-2 py-0.5 rounded border border-amber-200 text-[11px]">
                {c.reason}
              </span>
            </div>

            {/* Indic Discrepancy Box if present */}
            {c.indic_comparison && (
              <div className="bg-slate-50 p-2.5 rounded border border-slate-200 space-y-1 text-xs">
                <div className="flex items-center gap-1 font-bold text-slate-900 text-[11px]">
                  <ShieldCheck className="w-3.5 h-3.5 text-blue-900" />
                  <span>Indic Identity Resolution • {c.indic_comparison.similarity}</span>
                </div>
                <div className="text-slate-700 text-[11px] space-y-0.5 font-mono">
                  <p><span className="text-slate-500 font-sans">Aadhaar:</span> {c.indic_comparison.source_a}</p>
                  <p><span className="text-slate-500 font-sans">School:</span> {c.indic_comparison.source_b}</p>
                  <p><span className="text-slate-500 font-sans">Devanagari:</span> {c.indic_comparison.devnagari}</p>
                </div>
              </div>
            )}

            {/* Verification Evidence */}
            <div className="text-xs text-slate-600 bg-slate-50 p-2.5 rounded border border-slate-200 leading-relaxed">
              <span className="font-bold text-slate-800 block mb-0.5">Verification Evidence:</span>
              {c.explanation}
            </div>

            {/* Decision Status or Action Buttons */}
            {c.status === 'PENDING' ? (
              <div className="flex items-center gap-2 pt-1 border-t border-slate-100">
                <button
                  onClick={() => handleDecision(c.id, 'APPROVED')}
                  className="flex-1 py-1.5 bg-blue-900 hover:bg-blue-800 text-white font-semibold text-xs rounded transition flex items-center justify-center gap-1.5 shadow-2xs"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Approve Sanction</span>
                </button>
                <button
                  onClick={() => handleDecision(c.id, 'REJECTED')}
                  className="px-3 py-1.5 bg-white hover:bg-rose-50 text-rose-700 border border-rose-200 font-semibold text-xs rounded transition flex items-center justify-center gap-1"
                >
                  <XCircle className="w-3.5 h-3.5" />
                  <span>Reject</span>
                </button>
              </div>
            ) : (
              <div className="pt-1 border-t border-slate-100 flex items-center justify-between text-xs">
                <span className="text-slate-500 font-medium">Status:</span>
                <span className={`font-bold px-2 py-0.5 rounded border ${
                  c.status === 'APPROVED' ? 'bg-emerald-50 text-emerald-800 border-emerald-200' : 'bg-rose-50 text-rose-800 border-rose-200'
                }`}>
                  {c.status === 'APPROVED' ? 'APPROVED & SANCTIONED' : 'APPLICATION REJECTED'}
                </span>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* DESKTOP TABLE VIEW (>= 768px) */}
      <div className="hidden md:block bg-white rounded-lg border border-slate-200 shadow-2xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50 text-[11px] font-bold uppercase tracking-wider text-slate-500">
              <tr>
                <th scope="col" className="px-4 py-3 text-left">Application ID</th>
                <th scope="col" className="px-4 py-3 text-left">Candidate & Domicile</th>
                <th scope="col" className="px-4 py-3 text-left">Scheme</th>
                <th scope="col" className="px-4 py-3 text-left">Exception Reason</th>
                <th scope="col" className="px-4 py-3 text-center">SLA Clock</th>
                <th scope="col" className="px-4 py-3 text-center">Status</th>
                <th scope="col" className="px-4 py-3 text-right">Administrative Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs font-medium text-slate-700">
              {filteredCases.map((c) => (
                <React.Fragment key={c.id}>
                  <tr 
                    className={`cursor-pointer hover:bg-slate-50 transition-colors ${
                      expandedId === c.id ? 'bg-slate-50/80' : ''
                    }`}
                    onClick={() => setExpandedId(expandedId === c.id ? null : c.id)}
                  >
                    <td className="px-4 py-3.5 whitespace-nowrap">
                      <span className="font-mono font-bold text-blue-900 block">{c.application_id}</span>
                      <span className="text-[10px] text-slate-400">Click to inspect</span>
                    </td>
                    <td className="px-4 py-3.5 whitespace-nowrap">
                      <div className="font-bold text-slate-900 text-sm">{c.student_name}</div>
                      <div className="text-[11px] text-slate-500">{c.state}</div>
                    </td>
                    <td className="px-4 py-3.5 max-w-xs truncate text-slate-600">
                      {c.scheme}
                    </td>
                    <td className="px-4 py-3.5 whitespace-nowrap">
                      <span className="bg-amber-50 text-amber-900 border border-amber-200 font-semibold px-2 py-0.5 rounded text-[11px]">
                        {c.reason}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 whitespace-nowrap text-center">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold border ${
                        c.days_remaining <= 1 ? 'bg-rose-50 text-rose-700 border-rose-200' :
                        c.days_remaining <= 3 ? 'bg-amber-50 text-amber-700 border-amber-200' :
                        'bg-slate-50 text-slate-600 border-slate-200'
                      }`}>
                        <Clock className="w-3 h-3" />
                        {c.days_remaining}d left
                      </span>
                    </td>
                    <td className="px-4 py-3.5 whitespace-nowrap text-center">
                      <span className={`font-semibold px-2 py-0.5 rounded text-[11px] border ${
                        c.status === 'APPROVED' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                        c.status === 'REJECTED' ? 'bg-rose-50 text-rose-700 border-rose-200' :
                        'bg-slate-100 text-slate-700 border-slate-200'
                      }`}>
                        {c.status}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 whitespace-nowrap text-right">
                      {c.status === 'PENDING' ? (
                        <div className="inline-flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
                          <button
                            onClick={() => handleDecision(c.id, 'APPROVED')}
                            className="px-2.5 py-1 bg-blue-900 hover:bg-blue-800 text-white font-semibold rounded text-xs transition shadow-2xs"
                          >
                            Approve
                          </button>
                          <button
                            onClick={() => handleDecision(c.id, 'REJECTED')}
                            className="px-2.5 py-1 bg-white hover:bg-rose-50 text-rose-700 border border-rose-200 font-semibold rounded text-xs transition"
                          >
                            Reject
                          </button>
                        </div>
                      ) : (
                        <span className="text-slate-400 text-xs font-mono">Logged to Ledger</span>
                      )}
                    </td>
                  </tr>

                  {/* Expandable Evidence Inspection Drawer */}
                  {expandedId === c.id && (
                    <tr>
                      <td colSpan={7} className="bg-slate-50 px-5 py-4 border-y border-slate-200">
                        <div className="bg-white p-4 rounded border border-slate-200 shadow-2xs space-y-3">
                          <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                            <span className="text-xs font-bold uppercase tracking-wider text-slate-800 flex items-center gap-1.5">
                              <ShieldCheck className="w-4 h-4 text-blue-900" />
                              Cryptographic Evidence & Indic Corroboration Engine
                            </span>
                            <span className="text-xs text-slate-500 font-mono">Reference: {c.evidence_type}</span>
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                            <div>
                              <span className="font-bold text-slate-800 block mb-1">Grounded Reasoning:</span>
                              <p className="text-slate-600 leading-relaxed bg-slate-50 p-2.5 rounded border border-slate-200">
                                {c.explanation}
                              </p>
                            </div>
                            
                            {c.indic_comparison && (
                              <div className="bg-slate-50 p-2.5 rounded border border-slate-200 space-y-1 text-slate-700">
                                <span className="font-bold text-slate-800 block mb-1">Phonological Resolution Metrics:</span>
                                <p><span className="text-slate-500">Record A (UIDAI):</span> <strong className="text-slate-900">{c.indic_comparison.source_a}</strong></p>
                                <p><span className="text-slate-500">Record B (School):</span> <strong className="text-slate-900">{c.indic_comparison.source_b}</strong></p>
                                <p><span className="text-slate-500">Canonical Devanagari:</span> <strong className="text-slate-900">{c.indic_comparison.devnagari}</strong></p>
                                <p><span className="text-slate-500">Double Metaphone Score:</span> <strong className="text-emerald-700">{c.indic_comparison.similarity}</strong></p>
                              </div>
                            )}
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
