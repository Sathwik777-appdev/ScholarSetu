import { useEffect, useState } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import Sidebar, { BrandMark } from './Sidebar';
import { Loading } from './States';
import { useAuth } from '../auth/auth';

export default function Layout() {
  const { user, checking } = useAuth();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  useEffect(() => setMenuOpen(false), [location.pathname]);

  if (checking) return <div className="p-8"><Loading label="Checking your session…" /></div>;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;

  return (
    <div className="flex min-h-dvh">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[60] focus:rounded-lg focus:bg-white focus:px-3 focus:py-2 focus:text-sm focus:shadow-lift">Skip to content</a>
      <aside className="no-print sticky top-0 hidden h-dvh w-[17rem] shrink-0 lg:block">
        <Sidebar />
      </aside>
      {menuOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-ink-950/60 backdrop-blur-sm" onClick={() => setMenuOpen(false)} />
          <div 
            className="absolute inset-y-0 left-0 w-72 shadow-lift bg-white"
            style={{
              paddingTop: 'max(env(safe-area-inset-top, 0px), 16px)',
              paddingBottom: 'max(env(safe-area-inset-bottom, 0px), 16px)'
            }}
          >
            <button onClick={() => setMenuOpen(false)} className="absolute right-3 top-5 z-10 p-1 text-slate-400" aria-label="Close menu">
              <X className="w-5 h-5" />
            </button>
            <Sidebar onNavigate={() => setMenuOpen(false)} />
          </div>
        </div>
      )}
      <div className="flex-1 flex flex-col min-w-0">
        <header 
          className="mobile-bar sticky top-0 z-30 flex items-center gap-3 border-b border-slate-200/70 bg-white/85 px-4 py-3 backdrop-blur-xl lg:hidden"
          style={{
            paddingTop: 'max(env(safe-area-inset-top, 0px), 14px)'
          }}
        >
          <button onClick={() => setMenuOpen(true)} className="rounded-lg p-1.5 text-slate-700 hover:bg-slate-100" aria-label="Open menu">
            <Menu className="w-5 h-5" />
          </button>
          <BrandMark className="h-7 w-7" />
          <span className="font-semibold tracking-tight">ScholarSetu</span>
        </header>
        <main id="main" className="flex-1">
          <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-10 lg:py-9">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
