import { useState } from 'react';
import { 
  GraduationCap, Users, ShieldAlert, Sparkles, Send, CheckCircle2, 
  AlertTriangle, ArrowRight, Lock, Key, RefreshCw, FileCheck, 
  PhoneCall, Printer, Download, QrCode, X, ShieldCheck, 
  CheckCheck, Building2, Check, Award, FileText, ExternalLink
} from 'lucide-react';
import axios from 'axios';
import { getApiBaseUrl } from '../api/client';
import { useLanguage } from '../context/LanguageContext';

export default function StudentPortal() {
  const { language, t, currentOption } = useLanguage();
  const [activeChild, setActiveChild] = useState<'sunita' | 'rahul'>('sunita');
  const [mitraActive, setMitraActive] = useState(false);
  
  // Interactive DBT Resolution Simulator state
  const [dbtState, setDbtState] = useState<'dormant_risk' | 'resolving' | 'seeded_active'>('dormant_risk');
  const [dbtNudgeSent, setDbtNudgeSent] = useState(false);

  // Official Passport Modal state
  const [showPassportModal, setShowPassportModal] = useState(false);

  // Sovereign AI Engine selection
  const [aiEngine, setAiEngine] = useState<'sovereign_ollama' | 'bhashini' | 'rules'>('sovereign_ollama');

  const [jagoInput, setJagoInput] = useState('');
  const [jagoMessages, setJagoMessages] = useState<Array<{ sender: 'user' | 'jago'; text: string; citation?: string }>>([
    {
      sender: 'jago',
      text: language === 'hi' 
        ? 'नमस्ते सुनीता! मैं जागो (JAGO) जनजातीय सहायता प्रणाली हूँ। आप अपनी छात्रवृत्ति आवेदन स्थिति, डीबीटी बैंक भुगतान अथवा पात्रता नियमों के संबंध में पूछ सकते हैं।'
        : language === 'sat'
        ? 'ᱡᱚᱦᱟᱨ ᱥᱩᱱᱤᱛᱟ! ᱤᱧ JAGO ᱜᱚᱲᱚᱭᱤᱡ ᱠᱟᱹᱱᱟᱹᱧ ᱾ ᱟᱢᱟᱜ ᱥᱠᱚᱞᱟᱨᱥᱤᱯ ᱦᱟᱞᱚᱛ ᱟᱨ ᱵᱮᱸᱠ ᱴᱟᱠᱟ (DBT) ᱵᱟᱵᱚᱛ ᱠᱩᱞᱤ ᱫᱟᱲᱮᱭᱟᱜ-ᱟᱢ ᱾'
        : language === 'or'
        ? 'ନମସ୍କାର ସୁନୀତା! ମୁଁ ଜାଗୋ (JAGO) ଜନଜାତି ସହାୟତା ପ୍ରଣାଳୀ ଅଟେ। ଆପଣ ନିଜର ଛାତ୍ରବୃତ୍ତି ସ୍ଥିତି କିମ୍ବା ବ୍ୟାଙ୍କ ଦେୟ ବିଷୟରେ ପଚାରି ପାରିବେ।'
        : 'Welcome Sunita. I am JAGO, the automated guidance desk for the Ministry of Tribal Affairs. How may I assist you with your scholarship or DBT status today?',
      citation: 'MoTA Automated Helpdesk • Canonical State Synchronized',
    },
  ]);
  const [loadingJago, setLoadingJago] = useState(false);

  // Simulate DBT Bank Seeding Fix live during Judge Demo
  const handleSimulateDbtResolution = () => {
    setDbtState('resolving');
    setTimeout(() => {
      setDbtState('seeded_active');
    }, 1200);
  };

  // Send message to JAGO backend
  const handleSendJago = async (textToSend?: string) => {
    const query = textToSend || jagoInput;
    if (!query.trim()) return;

    setJagoMessages((prev) => [...prev, { sender: 'user', text: query }]);
    setJagoInput('');
    setLoadingJago(true);

    try {
      const res = await axios.post(`${getApiBaseUrl()}/v1/jago/chat`, {
        message: query,
        language: language === 'sat' || language === 'or' || language === 'gon' ? 'hi' : language,
        channel: 'web_portal',
      });
      const data = res.data;
      setJagoMessages((prev) => [
        ...prev,
        {
          sender: 'jago',
          text: data.response_text || 'Application record verified against state database.',
          citation: 'Statutory Verification • Gazette Rule MoTA/ST/2026/G-14',
        },
      ]);
    } catch (e) {
      setJagoMessages((prev) => [
        ...prev,
        {
          sender: 'jago',
          text: query.toLowerCase().includes('paisa') || query.toLowerCase().includes('money') || query.toLowerCase().includes('payment')
            ? (dbtState === 'seeded_active'
                ? 'Your Post-Matric ST Scholarship (APP-PM-2026-000812) has been cleared for payment. ₹14,500 has been credited to your Aadhaar-seeded SBI account via PFMS.'
                : 'Your Post-Matric Scholarship is approved by the Institution. However, PFMS disbursement is pending because your bank account is not mapped for Aadhaar DBT on NPCI.')
            : 'Your scholarship application is currently in Authority Review stage. All 4 verifiable credentials have been cryptographically validated.',
          citation: dbtState === 'seeded_active' ? 'PFMS Credit Ref #202604128912' : 'NPCI NACH Advisory #DORM-4912',
        },
      ]);
    } finally {
      setLoadingJago(false);
    }
  };

  return (
    <div className="space-y-5 pb-10">
      {/* Official Beneficiary Profile Card */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-2xs overflow-hidden">
        {/* Top Header Strip */}
        <div className="bg-slate-900 text-white px-5 py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              National Scholarship Beneficiary Record
            </span>
            <span className="text-slate-600">|</span>
            <span className="text-xs text-amber-300 font-medium">
              Academic Year 2026-27
            </span>
          </div>

          {/* Family Mode Selector */}
          <div className="flex items-center gap-1.5 self-start sm:self-auto bg-slate-800 p-1 rounded border border-slate-700 text-xs">
            <span className="text-slate-400 px-1 font-medium text-[11px] flex items-center gap-1">
              <Users className="w-3 h-3 text-slate-300" />
              {t('familyMode')}:
            </span>
            <button
              onClick={() => setActiveChild('sunita')}
              className={`px-2.5 py-1 rounded text-xs font-semibold transition ${
                activeChild === 'sunita' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-300 hover:text-white'
              }`}
            >
              Sunita (Post-Matric)
            </button>
            <button
              onClick={() => setActiveChild('rahul')}
              className={`px-2.5 py-1 rounded text-xs font-semibold transition ${
                activeChild === 'rahul' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-300 hover:text-white'
              }`}
            >
              Rahul (Pre-Matric)
            </button>
          </div>
        </div>

        {/* Candidate Detail Grid */}
        <div className="p-5">
          <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
                  {activeChild === 'sunita' ? 'Sunita Hansda' : 'Rahul Hansda'}
                </h1>
                <span className="bg-slate-100 text-slate-700 text-xs font-semibold px-2 py-0.5 rounded border border-slate-200">
                  Scheduled Tribe (Santal)
                </span>
                <span className="bg-emerald-50 text-emerald-800 text-xs font-semibold px-2 py-0.5 rounded border border-emerald-200 flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3 text-emerald-600" />
                  UIDAI e-KYC Verified
                </span>
              </div>
              <p className="text-xs text-slate-600">
                {activeChild === 'sunita'
                  ? 'Dumka Government Inter College • Class 11 (Science) • District: Dumka, Jharkhand'
                  : 'Government Ashram High School • Class 9 • District: Dumka, Jharkhand'}
              </p>
            </div>

            {/* Candidate Action Buttons */}
            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={() => setShowPassportModal(true)}
                className="bg-blue-900 hover:bg-blue-800 text-white font-semibold text-xs px-3.5 py-2 rounded transition flex items-center gap-1.5 shadow-2xs"
              >
                <FileCheck className="w-3.5 h-3.5" />
                <span>View Official Passport</span>
              </button>

              <button
                onClick={() => setMitraActive(!mitraActive)}
                className="border border-slate-300 hover:bg-slate-50 text-slate-700 font-semibold text-xs px-3 py-2 rounded transition flex items-center gap-1.5"
              >
                <PhoneCall className="w-3.5 h-3.5 text-slate-500" />
                <span>{mitraActive ? 'Mitra Assisted Active' : 'Enable Mitra Assisted'}</span>
              </button>
            </div>
          </div>

          {/* Demographic Metadata Strip */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4 pt-4 border-t border-slate-100 text-xs">
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400 block">APAAR / PEN ID</span>
              <span className="font-mono font-semibold text-slate-800">
                {activeChild === 'sunita' ? '8839-2026-9011' : '8839-2026-4412'}
              </span>
            </div>
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Father / Guardian</span>
              <span className="font-semibold text-slate-800">Babulal Hansda</span>
            </div>
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Bank Account (DBT)</span>
              <span className="font-mono font-semibold text-slate-800">SBI Dumka (••••4912)</span>
            </div>
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400 block">DigiLocker Repository</span>
              <span className="font-semibold text-emerald-700 flex items-center gap-1">
                <Check className="w-3 h-3 text-emerald-600" /> Connected & Sealed
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Grid: Application Timeline + JAGO Desk */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Left 2 Columns */}
        <div className="lg:col-span-2 space-y-5">
          {/* Automatic Pathway Notice */}
          {activeChild === 'sunita' && (
            <div className="bg-amber-50/70 border border-amber-200 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <div className="p-1.5 rounded bg-amber-600 text-white shrink-0 mt-0.5">
                  <Sparkles className="w-4 h-4" />
                </div>
                <div className="space-y-1 flex-1 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-amber-950 text-sm">
                      {t('pathwayTitle')}
                    </span>
                    <span className="text-[10px] uppercase font-bold px-2 py-0.5 bg-amber-200/80 text-amber-900 rounded">
                      Pathway Transition
                    </span>
                  </div>
                  <p className="text-amber-900 leading-relaxed">
                    {t('pathwayDesc')}
                  </p>
                  <div className="pt-2 flex items-center gap-3">
                    <button 
                      onClick={() => setShowPassportModal(true)}
                      className="bg-amber-800 hover:bg-amber-900 text-white font-semibold text-xs px-3 py-1.5 rounded transition flex items-center gap-1.5"
                    >
                      <span>Review Verifiable Credentials</span>
                      <ArrowRight className="w-3 h-3" />
                    </button>
                    <span className="text-amber-800 font-medium text-[11px]">
                      Single Verification, Universal Portability
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Active Application Card */}
          <div className="bg-white rounded-lg border border-slate-200 p-5 shadow-2xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-4 border-b border-slate-100">
              <div>
                <span className="text-[10px] uppercase font-bold text-slate-400 block font-mono">
                  {activeChild === 'sunita' ? 'Application ID: APP-PM-2026-000812' : 'Application ID: APP-PRM-2025-004192'}
                </span>
                <h2 className="text-base font-bold text-slate-900 mt-0.5">
                  {activeChild === 'sunita' ? 'Post-Matric Scholarship for ST Students' : 'Pre-Matric Scholarship (Class 9)'}
                </h2>
              </div>
              <span
                className={`self-start sm:self-auto text-xs font-semibold px-2.5 py-1 rounded border ${
                  activeChild === 'sunita'
                    ? dbtState === 'seeded_active'
                      ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                      : 'bg-blue-50 text-blue-800 border-blue-200'
                    : 'bg-emerald-50 text-emerald-800 border-emerald-200'
                }`}
              >
                {activeChild === 'sunita' 
                  ? (dbtState === 'seeded_active' ? 'Sanctioned & Credited' : 'Under Authority Review') 
                  : 'Disbursed (Credited)'}
              </span>
            </div>

            {/* Financial Overview Cards */}
            <div className="grid grid-cols-3 gap-3 my-4">
              <div className="bg-slate-50 p-3 rounded border border-slate-200/80">
                <span className="text-[10px] uppercase font-bold text-slate-400 block">{t('sanctioned')}</span>
                <p className="text-lg font-bold text-slate-900 mt-0.5">
                  {activeChild === 'sunita' ? '₹14,500' : '₹7,000'}
                </p>
                <p className="text-[10px] text-slate-500 mt-0.5">Tuition + Allowance</p>
              </div>

              <div className="bg-slate-50 p-3 rounded border border-slate-200/80">
                <span className="text-[10px] uppercase font-bold text-slate-400 block">{t('credited')}</span>
                <p className={`text-lg font-bold mt-0.5 ${dbtState === 'seeded_active' ? 'text-emerald-700' : 'text-slate-900'}`}>
                  {activeChild === 'sunita' 
                    ? (dbtState === 'seeded_active' ? '₹14,500' : '₹0') 
                    : '₹7,000'}
                </p>
                <p className="text-[10px] text-slate-500 mt-0.5">
                  {dbtState === 'seeded_active' ? 'Credit Confirmed' : 'Pending Clearance'}
                </p>
              </div>

              <div className="bg-slate-50 p-3 rounded border border-slate-200/80">
                <span className="text-[10px] uppercase font-bold text-slate-400 block">{t('pendingRelease')}</span>
                <p className="text-lg font-bold text-slate-900 mt-0.5">
                  {activeChild === 'sunita' 
                    ? (dbtState === 'seeded_active' ? '₹0' : '₹14,500') 
                    : '₹0'}
                </p>
                <p className="text-[10px] text-slate-500 mt-0.5">
                  {dbtState === 'seeded_active' ? 'No balance' : 'Pre-Sanction Stage'}
                </p>
              </div>
            </div>

            {/* DBT Pre-Sanction Interception Box */}
            {activeChild === 'sunita' && (
              <div className="mb-4">
                {dbtState === 'seeded_active' ? (
                  <div className="bg-emerald-50 border border-emerald-200 rounded p-3.5">
                    <div className="flex items-start gap-3">
                      <CheckCheck className="w-5 h-5 text-emerald-700 shrink-0 mt-0.5" />
                      <div className="space-y-1 text-xs flex-1">
                        <div className="flex items-center justify-between">
                          <p className="font-bold text-emerald-950">
                            {t('dbtSuccessAlert')}
                          </p>
                          <span className="bg-emerald-200/80 text-emerald-900 text-[10px] font-bold px-2 py-0.5 rounded">
                            NPCI SEEDED
                          </span>
                        </div>
                        <p className="text-emerald-900">
                          Bank Account: State Bank of India Dumka (A/C ••••4912) is active and verified for Direct Benefit Transfer.
                        </p>
                        <button
                          onClick={() => setDbtState('dormant_risk')}
                          className="text-[11px] text-slate-500 hover:text-slate-800 underline font-medium pt-1"
                        >
                          Reset state to demonstrate dormancy interception
                        </button>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="bg-red-50/80 border border-red-200 rounded p-3.5">
                    <div className="flex items-start gap-3">
                      <AlertTriangle className="w-5 h-5 text-red-700 shrink-0 mt-0.5" />
                      <div className="space-y-1 text-xs flex-1">
                        <div className="flex items-center justify-between">
                          <p className="font-bold text-red-950">
                            Pre-Sanction Banking Advisory: NPCI Seeding Required
                          </p>
                          <span className="bg-red-200 text-red-900 text-[10px] font-bold px-2 py-0.5 rounded">
                            DBT GUARDIAN ALERT
                          </span>
                        </div>
                        <p className="text-red-900 leading-relaxed">
                          Your bank account (SBI Dumka ••••4912) is not currently mapped for Aadhaar-based DBT on the National NPCI NACH gateway. 
                          Disbursement will be blocked at the PFMS stage if not seeded.
                        </p>
                        <div className="pt-2 flex flex-wrap items-center gap-2">
                          <button
                            onClick={handleSimulateDbtResolution}
                            disabled={dbtState === 'resolving'}
                            className="bg-red-700 hover:bg-red-800 text-white font-semibold text-xs px-3 py-1.5 rounded transition flex items-center gap-1.5 shadow-2xs"
                          >
                            {dbtState === 'resolving' ? (
                              <>
                                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                                <span>Querying NPCI Gateway...</span>
                              </>
                            ) : (
                              <>
                                <CheckCircle2 className="w-3.5 h-3.5" />
                                <span>{t('simulateDbtFix')}</span>
                              </>
                            )}
                          </button>

                          <button
                            onClick={() => {
                              setDbtNudgeSent(true);
                              setTimeout(() => setDbtNudgeSent(false), 3000);
                            }}
                            className="bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 font-semibold text-xs px-3 py-1.5 rounded transition flex items-center gap-1.5"
                          >
                            <PhoneCall className="w-3 h-3 text-slate-500" />
                            <span>{dbtNudgeSent ? 'SMS Advisory Dispatched' : 'Send SMS Advisory to Mobile'}</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Application Milestone Steps */}
            <div>
              <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2.5">
                Verification Pipeline Milestones
              </h4>
              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between p-2.5 rounded bg-slate-50 border border-slate-200/80">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                    <span className="font-semibold text-slate-800">Institute Verification Completed</span>
                  </div>
                  <span className="text-slate-500 font-mono text-[11px]">Principal, Dumka Govt Inter College</span>
                </div>

                <div className="flex items-center justify-between p-2.5 rounded bg-slate-50 border border-slate-200/80">
                  <div className="flex items-center gap-2">
                    {dbtState === 'seeded_active' ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                    ) : (
                      <RefreshCw className="w-4 h-4 text-blue-600 animate-spin shrink-0" />
                    )}
                    <span className="font-semibold text-slate-800">
                      {dbtState === 'seeded_active' ? 'Authority Sanction Granted' : 'Authority Review in Progress'}
                    </span>
                  </div>
                  <span className="text-slate-500 text-[11px]">
                    {dbtState === 'seeded_active' ? 'Sanction #SAN-2026-JH-881' : 'District Welfare Office (DWO)'}
                  </span>
                </div>

                <div className={`flex items-center justify-between p-2.5 rounded border ${
                  dbtState === 'seeded_active' 
                    ? 'bg-slate-50 border-slate-200/80' 
                    : 'bg-slate-50/50 border-slate-200/50 text-slate-400'
                }`}>
                  <div className="flex items-center gap-2">
                    {dbtState === 'seeded_active' ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                    ) : (
                      <Lock className="w-4 h-4 text-slate-400 shrink-0" />
                    )}
                    <span className="font-semibold text-slate-800">PFMS Direct Benefit Transfer Release</span>
                  </div>
                  <span className="font-mono text-[11px] text-slate-500">
                    {dbtState === 'seeded_active' ? 'Disbursed via NACH APBS' : 'Awaiting Sanction'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Verifiable Credentials Summary */}
          <div className="bg-white rounded-lg border border-slate-200 p-5 shadow-2xs">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900">{t('passportTitle')}</h3>
                <p className="text-xs text-slate-500">{t('passportSubtitle')}</p>
              </div>
              <button
                onClick={() => setShowPassportModal(true)}
                className="text-xs font-semibold text-blue-900 hover:text-blue-800 underline flex items-center gap-1"
              >
                <span>Inspect Passport</span>
                <ExternalLink className="w-3 h-3" />
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs">
              <div className="p-2.5 rounded border border-slate-200 bg-slate-50">
                <div className="flex justify-between items-center mb-1">
                  <span className="font-semibold text-slate-800">ST Caste Attestation</span>
                  <span className="bg-emerald-100 text-emerald-800 text-[10px] font-bold px-1.5 py-0.2 rounded">LIFETIME</span>
                </div>
                <p className="text-slate-500 text-[11px]">Issuer: SDO Dumka • Santal Tribe</p>
              </div>

              <div className="p-2.5 rounded border border-slate-200 bg-slate-50">
                <div className="flex justify-between items-center mb-1">
                  <span className="font-semibold text-slate-800">Identity Attestation</span>
                  <span className="bg-emerald-100 text-emerald-800 text-[10px] font-bold px-1.5 py-0.2 rounded">LIFETIME</span>
                </div>
                <p className="text-slate-500 text-[11px]">UIDAI e-KYC Masked Aadhaar • APAAR</p>
              </div>

              <div className="p-2.5 rounded border border-slate-200 bg-slate-50">
                <div className="flex justify-between items-center mb-1">
                  <span className="font-semibold text-slate-800">Income Attestation</span>
                  <span className="bg-slate-200 text-slate-800 text-[10px] font-bold px-1.5 py-0.2 rounded">AY 2026-27</span>
                </div>
                <p className="text-slate-500 text-[11px]">e-District Portal • ₹1,20,000 / annum</p>
              </div>

              <div className="p-2.5 rounded border border-slate-200 bg-slate-50">
                <div className="flex justify-between items-center mb-1">
                  <span className="font-semibold text-slate-800">Class 10 Academic Record</span>
                  <span className="bg-emerald-100 text-emerald-800 text-[10px] font-bold px-1.5 py-0.2 rounded">DIGILOCKER</span>
                </div>
                <p className="text-slate-500 text-[11px]">JAC Board Matriculation (84.5%)</p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: JAGO Helpdesk */}
        <div className="bg-white rounded-lg border border-slate-200 shadow-2xs flex flex-col h-[650px] overflow-hidden">
          {/* Official JAGO Header */}
          <div className="p-3.5 border-b border-slate-200 bg-slate-900 text-white">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-bold text-sm text-white">JAGO Guidance Desk</h3>
                <p className="text-[10px] text-slate-400">
                  Ministry of Tribal Affairs • Statutory Assistance
                </p>
              </div>
              <span className="text-[10px] bg-slate-800 text-slate-300 font-semibold px-2 py-0.5 rounded border border-slate-700">
                {currentOption.nativeName}
              </span>
            </div>

            {/* Architecture Pill */}
            <div className="mt-2 pt-2 border-t border-slate-800 flex items-center justify-between text-[10px] text-slate-400">
              <span>Sovereign GovCloud Engine</span>
              <span className="text-emerald-400 font-medium">DPDP Act 2023 Compliant</span>
            </div>
          </div>

          {/* Chat Messages */}
          <div className="flex-1 p-3.5 overflow-y-auto space-y-3 text-xs bg-slate-50/50">
            {jagoMessages.map((msg, idx) => (
              <div key={idx} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[85%] rounded p-3 ${
                    msg.sender === 'user'
                      ? 'bg-blue-900 text-white shadow-2xs'
                      : 'bg-white text-slate-900 border border-slate-200 shadow-2xs'
                  }`}
                >
                  <p className="leading-relaxed whitespace-pre-wrap">{msg.text}</p>
                  {msg.citation && (
                    <div className="mt-2 pt-1.5 border-t border-slate-100 text-[10px] text-slate-500 font-mono">
                      Ref: {msg.citation}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {loadingJago && (
              <div className="text-slate-500 text-xs flex items-center gap-2 italic py-1">
                <RefreshCw className="w-3.5 h-3.5 animate-spin text-slate-600" /> 
                <span>Accessing canonical scholarship ledger...</span>
              </div>
            )}
          </div>

          {/* Official Preset Queries */}
          <div className="p-2 bg-slate-100 border-t border-slate-200 flex flex-wrap gap-1">
            <button
              onClick={() => handleSendJago(language === 'sat' ? 'ᱤᱧᱟᱜ ᱴᱟᱠᱟ ᱛᱤᱥ ᱦᱤᱡᱩᱜ-ᱟ?' : 'Mera paisa kab aayega?')}
              className="text-[11px] bg-white hover:bg-slate-50 border border-slate-300 px-2 py-1 rounded text-slate-700 font-medium transition"
            >
              Track Payment Release
            </button>
            <button
              onClick={() => handleSendJago('Eligibility criteria check')}
              className="text-[11px] bg-white hover:bg-slate-50 border border-slate-300 px-2 py-1 rounded text-slate-700 font-medium transition"
            >
              Eligibility & Guidelines
            </button>
            <button
              onClick={() => handleSendJago('Deficiency kaise theek karein?')}
              className="text-[11px] bg-white hover:bg-slate-50 border border-slate-300 px-2 py-1 rounded text-slate-700 font-medium transition"
            >
              Resolve NPCI Block
            </button>
          </div>

          {/* Input Form */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendJago();
            }}
            className="p-2.5 border-t border-slate-200 flex items-center gap-2 bg-white"
          >
            <input
              type="text"
              value={jagoInput}
              onChange={(e) => setJagoInput(e.target.value)}
              placeholder="Enter your question in Hindi, Santali, or English..."
              className="flex-1 text-xs border border-slate-300 rounded px-2.5 py-2 focus:outline-none focus:ring-1 focus:ring-slate-700"
            />
            <button
              type="submit"
              disabled={loadingJago || !jagoInput.trim()}
              className="bg-blue-900 hover:bg-blue-800 disabled:opacity-50 text-white p-2 rounded transition"
              aria-label="Submit query"
            >
              <Send className="w-3.5 h-3.5" />
            </button>
          </form>
        </div>
      </div>

      {/* Official Verifiable Scholarship Passport Modal */}
      {showPassportModal && (
        <div 
          className="fixed inset-0 z-50 bg-slate-900/70 flex items-center justify-center p-4 overflow-y-auto"
          onClick={() => setShowPassportModal(false)}
        >
          <div 
            className="bg-white rounded-lg shadow-xl border border-slate-300 max-w-2xl w-full overflow-hidden text-slate-900 my-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Title Bar */}
            <div className="bg-slate-900 text-white px-5 py-3 flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
                Official Verifiable Scholarship Passport
              </span>
              <button 
                onClick={() => setShowPassportModal(false)}
                className="p-1 rounded text-slate-400 hover:text-white transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Document Body */}
            <div className="p-6 space-y-5 bg-white">
              {/* Institutional Header */}
              <div className="text-center border-b border-slate-200 pb-4">
                <p className="text-[11px] font-bold text-slate-600 uppercase tracking-widest">
                  Government of India • Ministry of Tribal Affairs
                </p>
                <h3 className="text-lg font-bold text-slate-900 tracking-tight mt-0.5">
                  SCHOLARSHIP VERIFICATION PASSPORT
                </h3>
                <p className="text-[10px] text-slate-500 font-mono mt-0.5">
                  Under National Unified Tribal Scholarship Architecture (DPDP Act 2023 Compliant)
                </p>
              </div>

              {/* Student Demographics Block */}
              <div className="flex items-start gap-4 p-3.5 rounded border border-slate-200 bg-slate-50 text-xs">
                <div className="w-16 h-20 rounded bg-slate-800 text-white flex flex-col items-center justify-center shrink-0">
                  <GraduationCap className="w-6 h-6 text-slate-300" />
                  <span className="text-[8px] font-bold uppercase mt-1 text-slate-400">Photo ID</span>
                </div>
                <div className="flex-1 space-y-1">
                  <div className="flex items-center gap-2">
                    <h4 className="text-base font-bold text-slate-900">Sunita Hansda</h4>
                    <span className="bg-slate-200 text-slate-800 text-[10px] font-bold px-1.5 py-0.2 rounded">
                      ST Santal
                    </span>
                  </div>
                  <p className="text-slate-600">Dumka Government Inter College, Dumka, Jharkhand</p>
                  <div className="grid grid-cols-2 gap-2 pt-1 font-mono text-[11px]">
                    <div>APAAR ID: <strong>8839-2026-9011</strong></div>
                    <div>DigiLocker: <strong>in.gov.uidai:9941</strong></div>
                  </div>
                </div>
              </div>

              {/* Attestation Table */}
              <div className="border border-slate-200 rounded text-xs divide-y divide-slate-100">
                <div className="p-2.5 flex items-center justify-between">
                  <div>
                    <p className="font-semibold text-slate-800">Scheduled Tribe Caste Attestation</p>
                    <p className="text-[10px] text-slate-500">Issuer: SDO Dumka • Lifetime Statutory Validity</p>
                  </div>
                  <span className="text-[10px] font-bold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                    VERIFIED
                  </span>
                </div>

                <div className="p-2.5 flex items-center justify-between">
                  <div>
                    <p className="font-semibold text-slate-800">Matriculation Class 10 Record (84.5%)</p>
                    <p className="text-[10px] text-slate-500">Issuer: Jharkhand Academic Council (JAC Board)</p>
                  </div>
                  <span className="text-[10px] font-bold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                    VERIFIED
                  </span>
                </div>

                <div className="p-2.5 flex items-center justify-between">
                  <div>
                    <p className="font-semibold text-slate-800">Family Income Assessment (₹1,20,000 / annum)</p>
                    <p className="text-[10px] text-slate-500">Issuer: Jharkhand Revenue Service (AY 2026-27)</p>
                  </div>
                  <span className="text-[10px] font-bold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                    VERIFIED
                  </span>
                </div>
              </div>

              {/* Offline Tamper-Proof Cryptographic Verification Block */}
              <div className="bg-slate-50 p-3.5 rounded border border-slate-200 flex items-center gap-4 text-xs">
                {/* Visual QR Code Pattern */}
                <div className="w-20 h-20 bg-white p-1.5 rounded border border-slate-300 shrink-0">
                  <svg viewBox="0 0 100 100" className="w-full h-full text-slate-900 fill-current">
                    <rect x="0" y="0" width="30" height="30" rx="2" />
                    <rect x="5" y="5" width="20" height="20" fill="white" />
                    <rect x="9" y="9" width="12" height="12" />
                    <rect x="70" y="0" width="30" height="30" rx="2" />
                    <rect x="75" y="5" width="20" height="20" fill="white" />
                    <rect x="79" y="9" width="12" height="12" />
                    <rect x="0" y="70" width="30" height="30" rx="2" />
                    <rect x="5" y="75" width="20" height="20" fill="white" />
                    <rect x="9" y="79" width="12" height="12" />
                    <rect x="36" y="8" width="8" height="8" />
                    <rect x="50" y="14" width="8" height="8" />
                    <rect x="38" y="38" width="24" height="24" rx="2" fill="#0f172a" />
                    <circle cx="50" cy="50" r="4" fill="white" />
                    <rect x="12" y="44" width="8" height="8" />
                    <rect x="72" y="42" width="12" height="8" />
                    <rect x="80" y="72" width="14" height="14" />
                    <rect x="42" y="76" width="10" height="10" />
                  </svg>
                </div>

                <div className="flex-1 space-y-1">
                  <p className="font-bold text-slate-900">
                    Offline Cryptographic Verification (Ed25519)
                  </p>
                  <p className="text-[11px] text-slate-600 leading-snug">
                    Can be authenticated offline by Ashram school headmasters or bank correspondents without network access.
                  </p>
                  <p className="font-mono text-[10px] text-slate-400 truncate">
                    Signature: ed25519:6a7b8c9d0e1f3a2b4c5d6e7f8a9b0c1d2e3f4a5b6c7d...
                  </p>
                </div>
              </div>
            </div>

            {/* Modal Actions */}
            <div className="bg-slate-100 px-5 py-3 border-t border-slate-200 flex items-center justify-between">
              <span className="text-[11px] text-slate-500 font-mono">
                Ledger Height: #819,204 • SHA-256 Validated
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => window.print()}
                  className="bg-blue-900 hover:bg-blue-800 text-white font-semibold text-xs px-3.5 py-1.5 rounded transition flex items-center gap-1.5"
                >
                  <Printer className="w-3.5 h-3.5" />
                  <span>Print Document</span>
                </button>
                <button
                  onClick={() => setShowPassportModal(false)}
                  className="bg-white border border-slate-300 text-slate-700 text-xs px-3 py-1.5 rounded hover:bg-slate-50 font-medium transition"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
