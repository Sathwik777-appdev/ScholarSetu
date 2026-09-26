import { useState, useRef, useEffect } from 'react';
import { Outlet, useLocation, Link, NavLink } from 'react-router-dom';
import Sidebar from './Sidebar';
import GovHeader from './GovHeader';
import { 
  Bell, GraduationCap, Building2, Menu, X, 
  LayoutDashboard, ClipboardCheck, Map, CreditCard, ShieldCheck,
  Globe, ChevronDown, Check
} from 'lucide-react';
import { useLanguage, SUPPORTED_LANGUAGES } from '../context/LanguageContext';

export default function Layout() {
  const location = useLocation();
  const isStudentView = location.pathname.startsWith('/student');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [mobileLangOpen, setMobileLangOpen] = useState(false);
  const mobileLangRef = useRef<HTMLDivElement>(null);
  const { language, setLanguage, currentOption, t } = useLanguage();

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (mobileLangRef.current && !mobileLangRef.current.contains(event.target as Node)) {
        setMobileLangOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="flex flex-col h-screen bg-slate-100 overflow-hidden font-sans">
      {/* Desktop Official Government of India & Tricolor Banner (Hidden on Mobile) */}
      <GovHeader />

      {/* Mobile Top App Header with Full Safe-Area Inset Clearance (Status Bar Protection) */}
      <div 
        className="lg:hidden w-full bg-slate-900 text-white shrink-0 z-40 border-b border-slate-800 shadow-sm"
        style={{
          paddingTop: 'max(env(safe-area-inset-top, 0px), 36px)',
        }}
      >
        {/* Official Indian National Tricolor Strip */}
        <div className="h-1 w-full grid grid-cols-3">
          <div className="bg-[#FF9933]" />
          <div className="bg-white" />
          <div className="bg-[#138808]" />
        </div>

        {/* Mobile Action Bar */}
        <div className="px-3.5 py-2.5 flex items-center justify-between">
          {/* Left: Hamburger & Brand */}
          <div className="flex items-center gap-2.5">
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="p-1.5 -ml-1 rounded-md text-slate-300 hover:text-white hover:bg-slate-800 active:bg-slate-700 transition"
              aria-label="Open navigation menu"
            >
              <Menu className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded bg-amber-400 text-slate-950 flex items-center justify-center font-bold text-xs shadow-xs">
                🏛️
              </div>
              <div>
                <span className="font-bold text-sm text-white tracking-tight leading-none block">
                  ScholarSetu
                </span>
                <span className="text-[9px] font-medium text-slate-400 tracking-tight leading-tight block">
                  MoTA • Govt of India
                </span>
              </div>
            </div>
          </div>

          {/* Right: Language Dropdown + Role Switcher */}
          <div className="flex items-center gap-2">
            {/* Language Selector Dropdown */}
            <div className="relative" ref={mobileLangRef}>
              <button
                onClick={() => setMobileLangOpen(!mobileLangOpen)}
                className="flex items-center gap-1 px-2 py-1 rounded text-xs font-semibold bg-slate-800 text-slate-200 border border-slate-700 active:bg-slate-700 transition"
                aria-label="Select Language"
              >
                <Globe className="w-3 h-3 text-slate-400" />
                <span className="text-[11px]">{currentOption.nativeName.split(' ')[0]}</span>
                <ChevronDown className="w-2.5 h-2.5 text-slate-400" />
              </button>

              {mobileLangOpen && (
                <div className="absolute right-0 mt-1 w-48 bg-white text-slate-900 rounded-md shadow-xl border border-slate-200 py-1 z-50">
                  <div className="px-3 py-1 text-[10px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-100">
                    Select Language / भाषा चुनें
                  </div>
                  {SUPPORTED_LANGUAGES.map((opt) => (
                    <button
                      key={opt.code}
                      onClick={() => {
                        setLanguage(opt.code);
                        setMobileLangOpen(false);
                      }}
                      className={`w-full px-3 py-1.5 text-left text-xs flex items-center justify-between hover:bg-slate-100 transition ${
                        language === opt.code ? 'bg-slate-50 text-blue-900 font-semibold' : 'text-slate-700'
                      }`}
                    >
                      <span>{opt.nativeName}</span>
                      {language === opt.code && <Check className="w-3.5 h-3.5 text-blue-800" />}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Role Switcher Pill */}
            <Link
              to={isStudentView ? '/dashboard' : '/student'}
              className="text-[11px] font-semibold bg-amber-400/15 hover:bg-amber-400/25 text-amber-300 px-2.5 py-1 rounded border border-amber-400/30 flex items-center gap-1 transition shadow-2xs"
            >
              {isStudentView ? (
                <>
                  <Building2 className="w-3 h-3 text-amber-300" />
                  <span>Ministry</span>
                </>
              ) : (
                <>
                  <GraduationCap className="w-3 h-3 text-amber-300" />
                  <span>Candidate</span>
                </>
              )}
            </Link>
          </div>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden relative">
        {/* Desktop Sidebar (Fixed left on desktop) */}
        <div className="hidden lg:flex lg:w-72 lg:flex-col shrink-0">
          <Sidebar />
        </div>

        {/* Mobile Drawer Backdrop */}
        {mobileMenuOpen && (
          <div 
            className="fixed inset-0 z-50 bg-slate-900/60 lg:hidden transition-opacity"
            onClick={() => setMobileMenuOpen(false)}
          />
        )}

        {/* Mobile Drawer */}
        <div 
          className={`fixed inset-y-0 left-0 z-50 w-72 bg-white shadow-xl transform transition-transform duration-250 ease-in-out lg:hidden flex flex-col ${
            mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
          }`}
          style={{
            paddingTop: 'max(env(safe-area-inset-top, 0px), 36px)',
            paddingBottom: 'max(env(safe-area-inset-bottom, 0px), 24px)'
          }}
        >
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded bg-slate-900 text-amber-400 flex items-center justify-center font-bold text-xs">
                🏛️
              </div>
              <div>
                <span className="font-bold text-sm text-slate-900 block leading-tight">ScholarSetu</span>
                <span className="text-[10px] text-slate-500 font-medium block">Ministry of Tribal Affairs</span>
              </div>
            </div>
            <button 
              onClick={() => setMobileMenuOpen(false)}
              className="p-1 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition"
              aria-label="Close menu"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto" onClick={() => setMobileMenuOpen(false)}>
            <Sidebar />
          </div>
        </div>

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          {/* Desktop Top Action Bar (Hidden on Mobile) */}
          <header className="hidden lg:flex shrink-0 bg-white border-b border-slate-200 px-6 py-2.5 items-center justify-between shadow-2xs">
            {/* Breadcrumb / Section Context */}
            <div className="flex items-center gap-2 text-xs">
              <span className="font-medium text-slate-500">
                {isStudentView ? 'Beneficiary Services' : 'Nodal Operations'}
              </span>
              <span className="text-slate-300">/</span>
              <span className="font-bold text-slate-800">
                {isStudentView ? 'Post-Matric ST Scholarship (Dumka)' : 'National Monitoring Dashboard'}
              </span>
            </div>

            {/* Right Desktop Header items */}
            <div className="flex items-center gap-3">
              {/* Role Toggle Pill (Clean Enterprise Style) */}
              <div className="inline-flex rounded-md bg-slate-100 p-0.5 border border-slate-200 text-xs">
                <Link
                  to="/student"
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded font-semibold transition ${
                    isStudentView
                      ? 'bg-white text-slate-900 shadow-2xs border border-slate-200'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <GraduationCap className="w-3.5 h-3.5 text-slate-600" />
                  <span>Candidate</span>
                </Link>
                <Link
                  to="/dashboard"
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded font-semibold transition ${
                    !isStudentView
                      ? 'bg-white text-slate-900 shadow-2xs border border-slate-200'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <Building2 className="w-3.5 h-3.5 text-slate-600" />
                  <span>Ministry</span>
                </Link>
              </div>

              {/* Notifications */}
              <button 
                type="button" 
                className="p-1.5 rounded text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition relative"
                aria-label="Notifications"
              >
                <Bell className="w-4 h-4" />
                <span className="absolute top-1 right-1 w-1.5 h-1.5 bg-amber-500 rounded-full" />
              </button>

              {/* User Identity Chip */}
              <div className="flex items-center gap-2 pl-2 border-l border-slate-200">
                <div className="w-7 h-7 rounded bg-slate-800 text-white flex items-center justify-center font-bold text-xs">
                  {isStudentView ? 'SH' : 'NO'}
                </div>
                <div className="text-left text-xs">
                  <p className="font-bold text-slate-900 leading-tight">
                    {isStudentView ? 'Sunita Hansda' : 'Nodal Officer (MoTA)'}
                  </p>
                  <p className="text-[10px] text-slate-500 font-medium">
                    {isStudentView ? 'Santal ST • Dumka' : 'Section Officer • DBT Cell'}
                  </p>
                </div>
              </div>
            </div>
          </header>

          {/* Scrollable Page Body */}
          <main className="flex-1 overflow-y-auto pb-32 lg:pb-8 overscroll-contain bg-slate-50">
            <div className="px-4 sm:px-6 lg:px-8 py-4 sm:py-5 max-w-7xl mx-auto">
              <Outlet />
            </div>
          </main>

          {/* Mobile Bottom Navigation Bar */}
          <nav 
            className="fixed bottom-0 inset-x-0 z-40 bg-white border-t border-slate-200 flex justify-around items-center lg:hidden shadow-md"
            style={{
              paddingTop: '6px',
              paddingBottom: 'max(env(safe-area-inset-bottom, 0px), 24px)',
            }}
          >
            <NavLink
              to="/student"
              className={({ isActive }) =>
                `flex flex-col items-center justify-center min-w-[3.5rem] py-1 px-2 rounded transition ${
                  isActive ? 'text-blue-900 font-bold' : 'text-slate-500 hover:text-slate-800'
                }`
              }
            >
              <GraduationCap className="w-4 h-4" />
              <span className="text-[10px] mt-0.5">Candidate</span>
            </NavLink>

            <NavLink
              to="/dashboard"
              className={({ isActive }) =>
                `flex flex-col items-center justify-center min-w-[3.5rem] py-1 px-2 rounded transition ${
                  isActive ? 'text-blue-900 font-bold' : 'text-slate-500 hover:text-slate-800'
                }`
              }
            >
              <LayoutDashboard className="w-4 h-4" />
              <span className="text-[10px] mt-0.5">Dashboard</span>
            </NavLink>

            <NavLink
              to="/review-queue"
              className={({ isActive }) =>
                `flex flex-col items-center justify-center min-w-[3.5rem] py-1 px-2 rounded transition ${
                  isActive ? 'text-blue-900 font-bold' : 'text-slate-500 hover:text-slate-800'
                }`
              }
            >
              <ClipboardCheck className="w-4 h-4" />
              <span className="text-[10px] mt-0.5">Review</span>
            </NavLink>

            <NavLink
              to="/coverage-map"
              className={({ isActive }) =>
                `flex flex-col items-center justify-center min-w-[3.5rem] py-1 px-2 rounded transition ${
                  isActive ? 'text-blue-900 font-bold' : 'text-slate-500 hover:text-slate-800'
                }`
              }
            >
              <Map className="w-4 h-4" />
              <span className="text-[10px] mt-0.5">Coverage</span>
            </NavLink>

            <NavLink
              to="/dbt-monitor"
              className={({ isActive }) =>
                `flex flex-col items-center justify-center min-w-[3.5rem] py-1 px-2 rounded transition ${
                  isActive ? 'text-blue-900 font-bold' : 'text-slate-500 hover:text-slate-800'
                }`
              }
            >
              <CreditCard className="w-4 h-4" />
              <span className="text-[10px] mt-0.5">DBT</span>
            </NavLink>
          </nav>
        </div>
      </div>
    </div>
  );
}
