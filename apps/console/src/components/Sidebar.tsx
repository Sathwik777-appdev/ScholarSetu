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
  { name: 'Coverage (Reach Radar)', href: '/coverage-map', icon: Map, analyticsOnly: true },
  { name: 'Bottlenecks and SLA', href: '/analytics', icon: BarChart3, analyticsOnly: true },
  { name: 'DBT failures', href: '/dbt-monitor', icon: CreditCard, analyticsOnly: true },
];

export default function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { user, logout } = useAuth();
  const canAnalyse = !!user && ANALYTICS_ROLES.includes(user.role);
  const jurisdiction = user?.role === 'MINISTRY' ? 'All India'
    : [user?.jurisdiction_district, user?.jurisdiction_state].filter(Boolean).join(', ');

  return (
    <div className="flex h-full flex-col border-r border-slate-200 bg-white px-3 py-4">
      <div className="px-2 pb-4 border-b border-slate-200">
        <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Ministry of Tribal Affairs</p>
        <p className="text-base font-bold text-slate-900">ScholarSetu console</p>
      </div>
      <nav className="flex-1 py-3">
        <ul className="space-y-1">
          {NAV.filter((item) => canAnalyse || !item.analyticsOnly).map((item) => (
            <li key={item.href}>
              <NavLink
                to={item.href}
                onClick={onNavigate}
                className={({ isActive }) =>
                  `flex items-center gap-2.5 rounded-md px-2 py-2 text-sm ${
                    isActive ? 'bg-slate-900 text-white font-semibold' : 'text-slate-700 hover:bg-slate-100'
                  }`
                }
              >
                <item.icon className="h-4 w-4 shrink-0" />
                {item.name}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      {user && (
        <div className="border-t border-slate-200 pt-3 px-2 text-xs">
          <p className="font-bold text-slate-900">{user.name}</p>
          <p className="text-slate-500">{ROLE_LABELS[user.role] ?? user.role}</p>
          {jurisdiction && <p className="text-slate-500">{jurisdiction}</p>}
          <button onClick={logout} className="mt-2 flex items-center gap-1 text-slate-600 hover:text-slate-900">
            <LogOut className="w-3.5 h-3.5" /> Sign out
          </button>
        </div>
      )}
    </div>
  );
}
