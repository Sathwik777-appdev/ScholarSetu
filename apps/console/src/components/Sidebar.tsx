import { NavLink } from 'react-router-dom';
import { BarChart3, ClipboardCheck, CreditCard, Inbox, LayoutDashboard, List, LogOut, Map, MessageSquare, RefreshCw, ShieldCheck, UserPlus } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { ANALYTICS_ROLES, useAuth } from '../auth/auth';
import { ROLE_LABELS } from '../utils/formatters';

interface NavItem {
  name: string;
  href: string;
  icon: LucideIcon;
  analyticsOnly?: boolean;
  ministryOnly?: boolean;
}

const GROUPS: { title: string; items: NavItem[] }[] = [
  { title: 'Work', items: [
    { name: 'My work', href: '/my-work', icon: Inbox },
    { name: 'Review queue', href: '/review-queue', icon: ClipboardCheck },
    { name: 'Applications', href: '/applications', icon: List },
  ] },
  { title: 'Insights', items: [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard, analyticsOnly: true },
    { name: 'Coverage', href: '/coverage-map', icon: Map, analyticsOnly: true },
    { name: 'Bottlenecks & SLA', href: '/analytics', icon: BarChart3, analyticsOnly: true },
    { name: 'DBT failures', href: '/dbt-monitor', icon: CreditCard, analyticsOnly: true },
  ] },
  { title: 'Administration', items: [
    { name: 'Data requests', href: '/data-requests', icon: ShieldCheck, analyticsOnly: true },
    { name: 'Portal sync', href: '/portal-sync', icon: RefreshCw },
    { name: 'Outreach', href: '/outreach', icon: MessageSquare },
    { name: 'Officers', href: '/manage-officers', icon: UserPlus, ministryOnly: true },
    { name: 'Demo SMS', href: '/demo-sms', icon: MessageSquare, ministryOnly: true },
  ] },
];

export function BrandMark({ className = 'h-9 w-9' }: { className?: string }) {
  return (
    <img src="/hero-logo.png" alt="ScholarSetu" className={`${className} object-contain`} />
  );
}

export default function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { user, logout } = useAuth();
  const canAnalyse = !!user && ANALYTICS_ROLES.includes(user.role);
  const jurisdiction = user?.role === 'MINISTRY' ? 'All India'
    : [user?.jurisdiction_district, user?.jurisdiction_state].filter(Boolean).join(', ');
  const initials = (user?.name ?? '?').split(/\s+/).map((w) => w[0]).slice(0, 2).join('').toUpperCase();
  const visible = (item: NavItem) => (canAnalyse || !item.analyticsOnly) && (!item.ministryOnly || user?.role === 'MINISTRY');

  return (
    <div className="relative flex h-full flex-col overflow-hidden bg-ink-950 text-slate-300">
      <div className="tricolour" />
      <div className="pointer-events-none absolute -left-24 -top-24 h-64 w-64 rounded-full bg-saffron-500/10 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-24 -right-24 h-64 w-64 rounded-full bg-chakra/20 blur-3xl" />
      <div className="relative flex flex-1 flex-col overflow-y-auto px-3 py-5">
        <div className="flex items-center gap-3 px-2 pb-5">
          <BrandMark />
          <div>
            <p className="text-[16px] font-semibold leading-none tracking-tight text-white">ScholarSetu</p>
            <p className="mt-1 text-[12px] text-slate-400">Ministry of Tribal Affairs</p>
          </div>
        </div>
        <nav className="flex-1" aria-label="Main">
          {GROUPS.map((g) => {
            const items = g.items.filter(visible);
            if (!items.length) return null;
            return (
              <div key={g.title} className="mb-4">
                <p className="px-3 pb-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">{g.title}</p>
                <ul className="space-y-0.5">
                  {items.map((item) => (
                    <li key={item.href}>
                      <NavLink
                        to={item.href}
                        onClick={onNavigate}
                        className={({ isActive }) =>
                          `group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-[14px] transition ${
                            isActive ? 'bg-gradient-to-r from-white/15 to-white/5 font-medium text-white shadow-[inset_0_0_0_1px_rgb(255_255_255/0.08)]'
                              : 'hover:bg-white/5 hover:text-white'}`
                        }
                      >
                        {({ isActive }) => (
                          <>
                            {isActive && <span className="absolute -left-3 top-2 bottom-2 w-1 rounded-r bg-saffron-400 shadow-[0_0_12px_rgb(255_180_84/0.8)]" />}
                            <item.icon className={`h-[18px] w-[18px] shrink-0 ${isActive ? 'text-saffron-400' : 'text-slate-500 group-hover:text-slate-300'}`} />
                            {item.name}
                          </>
                        )}
                      </NavLink>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </nav>
        {user && (
          <div className="mt-2 rounded-2xl bg-white/5 p-3 ring-1 ring-white/10 backdrop-blur">
            <div className="flex items-center gap-3">
              <div className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-gradient-to-br from-saffron-300 to-saffron-500 text-[13px] font-bold text-ink-950">{initials}</div>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-white">{user.name}</p>
                <p className="truncate text-[12px] text-slate-400">{ROLE_LABELS[user.role] ?? user.role}{jurisdiction && ` · ${jurisdiction}`}</p>
              </div>
            </div>
            <button onClick={logout} className="btn btn-ghost btn-sm mt-3 w-full !text-slate-300 hover:!bg-white/10 hover:!text-white">
              <LogOut className="h-3.5 w-3.5" /> Sign out
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
