import React from 'react';
import { useLanguage, SUPPORTED_LANGUAGES } from '../context/LanguageContext';
import { Globe, ChevronDown, Check, Building2, GraduationCap } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

export default function GovHeader() {
  const { language, setLanguage, currentOption } = useLanguage();
  const [langOpen, setLangOpen] = React.useState(false);
  const dropdownRef = React.useRef<HTMLDivElement>(null);
  const location = useLocation();
  const isStudentView = location.pathname.startsWith('/student');

  React.useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setLangOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="hidden lg:block w-full bg-white border-b border-slate-200 shrink-0">
      {/* Official Indian National Tricolor Strip */}
      <div className="h-1 w-full grid grid-cols-3">
        <div className="bg-[#FF9933]" />
        <div className="bg-white border-y border-slate-100" />
        <div className="bg-[#138808]" />
      </div>

      {/* Official Government Top Bar */}
      <div className="bg-slate-900 text-white text-[11px] px-3 sm:px-6 py-1 flex items-center justify-between">
        <div className="flex items-center gap-2 text-slate-300">
          <span className="font-semibold text-white">भारत सरकार</span>
          <span className="text-slate-500">|</span>
          <span>Government of India</span>
          <span className="hidden md:inline text-slate-500">•</span>
          <span className="hidden md:inline text-slate-300">National Unified Tribal Scholarship Portal</span>
        </div>

        <div className="flex items-center gap-3">
          {/* Language Switcher */}
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setLangOpen(!langOpen)}
              className="flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 transition"
              aria-label="Select Language"
            >
              <Globe className="w-3 h-3 text-slate-400" />
              <span>{currentOption.nativeName}</span>
              <ChevronDown className="w-2.5 h-2.5 text-slate-400" />
            </button>

            {langOpen && (
              <div className="absolute right-0 mt-1 w-52 bg-white text-slate-900 rounded-md shadow-lg border border-slate-200 py-1 z-50">
                <div className="px-3 py-1 text-[10px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-100">
                  Select Language / भाषा चुनें
                </div>
                {SUPPORTED_LANGUAGES.map((opt) => (
                  <button
                    key={opt.code}
                    onClick={() => {
                      setLanguage(opt.code);
                      setLangOpen(false);
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

          <span className="text-slate-500">|</span>

          {/* Quick Role Switcher */}
          <Link
            to={isStudentView ? '/dashboard' : '/student'}
            className="text-[11px] font-medium text-amber-300 hover:text-amber-200 transition flex items-center gap-1"
          >
            {isStudentView ? (
              <>
                <Building2 className="w-3 h-3" />
                <span>Ministry View</span>
              </>
            ) : (
              <>
                <GraduationCap className="w-3 h-3" />
                <span>Student View</span>
              </>
            )}
          </Link>
        </div>
      </div>
    </div>
  );
}
