import { NavLink } from 'react-router-dom';
import { BarChart3, ClipboardCheck, CreditCard, LayoutDashboard, List, LogOut, Map } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { ANALYTICS_ROLES, useAuth } from '../auth/AuthContext';
import { ROLE_LABELS } from '../utils/formatters';

interface NavItem {
  name: string;
  href: string;
  icon: LucideIcon;
  analyticsOnly?: boolean;
}

export const NAV: NavItem[] = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard, analyticsOnly: true },
  { name: 'Review queue', href: '/review-queue', icon: ClipboardCheck },
  { name: 'Applications', href: '/applications', icon: List },
  { name: 'Coverage', href: '/coverage-map', icon: Map, analyticsOnly: true },
  { name: 'Bottlenecks & SLA', href: '/analytics', icon: BarChart3, analyticsOnly: true },
  { name: 'DBT failures', href: '/dbt-monitor', icon: CreditCard, analyticsOnly: true },
];

export function BrandMark({ className = 'h-9 w-9' }: { className?: string }) {
  return (
    <div className={`${className} grid place-items-center rounded-xl bg-gradient-to-br from-saffron-400 to-saffron-500 shadow-lift`}>
      <svg viewBox="0 0 32 32" className="h-5 w-5" aria-hidden="true">
        <path d="M3 21h26M6 21c0-6 4.5-10 10-10s10 4 10 10" fill="none" stroke="#0c1326" strokeWidth="2.6" strokeLinecap="round" />
        <circle cx="16" cy="11" r="2.4" fill="#0c1326" />
      </svg>
    </div>
  );
}

export default function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { user, logout } = useAuth();
  const canAnalyse = !!user && ANALYTICS_ROLES.includes(user.role);
  const jurisdiction = user?.role === 'MINISTRY' ? 'All India'
    : [user?.jurisdiction_district, user?.jurisdiction_state].filter(Boolean).join(', ');
  const initials = (user?.name ?? '?').split(/\s+/).map((w) => w[0]).slice(0, 2).join('').toUpperCase();

  return (
    <div className="flex h-full flex-col bg-ink-950 text-slate-300 px-3 py-5">
      <div className="flex items-center gap-3 px-2 pb-6">
        <BrandMark />
        <div>
          <p className="text-[15px] font-semibold text-white tracking-tight">ScholarSetu</p>
          <p className="text-[11px] text-slate-400">Officer &amp; ministry console</p>
        </div>
      </div>
      <nav className="flex-1">
        <ul className="space-y-1">
          {NAV.filter((item) => canAnalyse || !item.analyticsOnly).map((item) => (
            <li key={item.href}>
              <NavLink
                to={item.href}
                onClick={onNavigate}
                className={({ isActive }) =>
                  `group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${
                    isActive ? 'bg-white/10 text-white font-medium' : 'hover:bg-white/5 hover:text-white'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    {isActive && <span className="absolute left-0 top-2 bottom-2 w-1 rounded-r bg-saffron-400" />}
                    <item.icon className={`h-4 w-4 shrink-0 ${isActive ? 'text-saffron-400' : 'text-slate-500 group-hover:text-slate-300'}`} />
                    {item.name}
                  </>
                )}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      {user && (
        <div className="mt-4 rounded-2xl bg-white/5 p-3 ring-1 ring-white/10">
          <div className="flex items-center gap-3">
            <div className="grid h-9 w-9 place-items-center rounded-full bg-gradient-to-br from-teal-400 to-teal-500 text-[13px] font-semibold text-ink-950">{initials}</div>
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-white">{user.name}</p>
              <p className="truncate text-[11px] text-slate-400">{ROLE_LABELS[user.role] ?? user.role}{jurisdiction && ` · ${jurisdiction}`}</p>
            </div>
          </div>
          <button onClick={logout} className="mt-3 flex w-full items-center justify-center gap-1.5 rounded-lg bg-white/5 py-1.5 text-xs text-slate-300 hover:bg-white/10 hover:text-white">
            <LogOut className="w-3.5 h-3.5" /> Sign out
          </button>
        </div>
      )}
    </div>
  );
}
