import { useEffect, useState } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import Sidebar, { BrandMark } from './Sidebar';
import { Loading } from './States';
import { useAuth } from '../auth/AuthContext';

export default function Layout() {
  const { user, checking } = useAuth();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  useEffect(() => setMenuOpen(false), [location.pathname]);

  if (checking) return <div className="p-8"><Loading label="Checking your session…" /></div>;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;

  return (
    <div className="flex h-dvh overflow-hidden bg-[#f4f6fb]">
      <aside className="hidden lg:block lg:w-68 w-64 shrink-0">
        <Sidebar />
      </aside>
      {menuOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-ink-950/60 backdrop-blur-sm" onClick={() => setMenuOpen(false)} />
          <div className="absolute inset-y-0 left-0 w-72 shadow-lift">
            <button onClick={() => setMenuOpen(false)} className="absolute right-3 top-5 z-10 p-1 text-slate-400" aria-label="Close menu">
              <X className="w-5 h-5" />
            </button>
            <Sidebar onNavigate={() => setMenuOpen(false)} />
          </div>
        </div>
      )}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="lg:hidden sticky top-0 z-30 flex items-center gap-3 border-b border-slate-200/70 bg-white/80 px-4 py-3 backdrop-blur-xl">
          <button onClick={() => setMenuOpen(true)} className="rounded-lg p-1.5 text-slate-700 hover:bg-slate-100" aria-label="Open menu">
            <Menu className="w-5 h-5" />
          </button>
          <BrandMark className="h-7 w-7" />
          <span className="font-semibold tracking-tight">ScholarSetu</span>
        </header>
        <main className="flex-1 overflow-y-auto">
          <div className="px-4 sm:px-6 lg:px-10 py-6 lg:py-8 max-w-7xl mx-auto">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
