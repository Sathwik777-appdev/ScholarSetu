import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, ClipboardCheck, Map, BarChart3, CreditCard, 
  Search, GraduationCap, ShieldCheck, Server, FileText
} from 'lucide-react';

const studentNav = [
  { name: 'Student Portal', sub: 'Candidate & Family View', href: '/student', icon: GraduationCap, badge: 'Direct' },
];

const officerNav = [
  { name: 'Executive Dashboard', sub: 'Disbursement & Pipeline', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Nodal Review Queue', sub: 'Indic Resolution & Verification', href: '/review-queue', icon: ClipboardCheck },
  { name: 'Coverage & Saturation', sub: 'Gram Panchayat & District Gap', href: '/coverage-map', icon: Map },
  { name: 'Analytics & SLA Monitor', sub: 'Institutional Velocity & Metrics', href: '/analytics', icon: BarChart3 },
  { name: 'DBT Failure Sentinel', sub: 'NPCI & PFMS Health Check', href: '/dbt-monitor', icon: CreditCard },
  { name: 'Student & APAAR Search', sub: 'Verification Mesh Registry', href: '/student-lookup', icon: Search },
];

export default function Sidebar() {
  return (
    <div className="flex grow flex-col gap-y-4 overflow-y-auto border-r border-slate-200 bg-white px-4 pb-4">
      {/* Official Government Institutional Seal & Identity */}
      <div className="pt-4 pb-3 border-b border-slate-200">
        <div className="flex items-start gap-3">
          {/* Emblem of India / Institutional Seal SVG */}
          <div className="w-10 h-10 rounded-md bg-slate-900 text-amber-400 flex items-center justify-center shrink-0 shadow-xs border border-slate-800">
            <svg viewBox="0 0 24 24" className="w-6 h-6 fill-current" aria-label="Government Emblem">
              <path d="M12 2L4 5v6.09c0 5.05 3.41 9.76 8 10.91 4.59-1.15 8-5.86 8-10.91V5l-8-3zm0 2.18l6 2.25v4.66c0 4.09-2.67 7.9-6 9.01-3.33-1.11-6-4.92-6-9.01V6.43l6-2.25zM11 7h2v6h-2V7zm0 8h2v2h-2v-2z"/>
            </svg>
          </div>
          <div className="min-w-0">
            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider leading-tight">
              Ministry of Tribal Affairs
            </p>
            <h1 className="text-base font-bold text-slate-900 tracking-tight leading-snug">
              ScholarSetu
            </h1>
            <p className="text-[10px] text-slate-600 font-medium">
              National Tribal Scholarship System
            </p>
          </div>
        </div>
      </div>

      {/* Navigation Sections */}
      <nav className="flex flex-1 flex-col justify-between">
        <ul role="list" className="flex flex-col gap-y-5">
          {/* Candidate & Family Experience */}
          <li>
            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5 px-2">
              Citizen & Beneficiary View
            </div>
            <ul role="list" className="space-y-1">
              {studentNav.map((item) => (
                <li key={item.name}>
                  <NavLink
                    to={item.href}
                    className={({ isActive }) =>
                      `group flex items-center justify-between rounded-md p-2 text-xs transition border ${
                        isActive
                          ? 'bg-slate-900 text-white font-semibold border-slate-900 shadow-xs'
                          : 'text-slate-700 hover:bg-slate-100 hover:text-slate-900 border-transparent'
                      }`
                    }
                  >
                    {({ isActive }) => (
                      <>
                        <div className="flex items-center gap-2.5 min-w-0">
                          <item.icon
                            className={`h-4 w-4 shrink-0 ${
                              isActive ? 'text-amber-400' : 'text-slate-500 group-hover:text-slate-800'
                            }`}
                          />
                          <div className="truncate">
                            <p className="truncate leading-tight">{item.name}</p>
                            <p className={`text-[10px] truncate ${isActive ? 'text-slate-300' : 'text-slate-400'}`}>
                              {item.sub}
                            </p>
                          </div>
                        </div>
                        <span className={`text-[9px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded ${
                          isActive ? 'bg-slate-800 text-amber-300' : 'bg-slate-100 text-slate-600'
                        }`}>
                          {item.badge}
                        </span>
                      </>
                    )}
                  </NavLink>
                </li>
              ))}
            </ul>
          </li>

          {/* Ministry & Nodal Console */}
          <li>
            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5 px-2">
              Ministry & Administration Console
            </div>
            <ul role="list" className="space-y-1">
              {officerNav.map((item) => (
                <li key={item.name}>
                  <NavLink
                    to={item.href}
                    className={({ isActive }) =>
                      `group flex items-center gap-2.5 rounded-md p-2 text-xs transition border ${
                        isActive
                          ? 'bg-slate-900 text-white font-semibold border-slate-900 shadow-xs'
                          : 'text-slate-700 hover:bg-slate-100 hover:text-slate-900 border-transparent'
                      }`
                    }
                  >
                    {({ isActive }) => (
                      <>
                        <item.icon
                          className={`h-4 w-4 shrink-0 ${
                            isActive ? 'text-amber-400' : 'text-slate-500 group-hover:text-slate-800'
                          }`}
                        />
                        <div className="min-w-0 flex-1 truncate">
                          <p className="truncate leading-tight">{item.name}</p>
                          <p className={`text-[10px] truncate ${isActive ? 'text-slate-300' : 'text-slate-400'}`}>
                            {item.sub}
                          </p>
                        </div>
                      </>
                    )}
                  </NavLink>
                </li>
              ))}
            </ul>
          </li>
        </ul>

        {/* Institutional System Status Footer */}
        <div className="pt-3 border-t border-slate-200 text-[11px] space-y-2">
          <div className="p-2.5 rounded-md bg-slate-50 border border-slate-200 space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-slate-600 uppercase tracking-wider flex items-center gap-1">
                <Server className="w-3 h-3 text-slate-500" />
                GovCloud Status
              </span>
              <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-700">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
                Active
              </span>
            </div>
            <p className="text-[10px] text-slate-500">
              NIC MeghRaj Infrastructure • Ed25519 Root Validated
            </p>
          </div>

          <div className="flex items-center justify-between text-[10px] text-slate-400 px-1 font-mono">
            <span>Core v1.0.0</span>
            <span>DPDP 2023 Compliant</span>
          </div>
        </div>
      </nav>
    </div>
  );
}
