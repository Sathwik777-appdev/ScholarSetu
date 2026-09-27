import { useState } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import Sidebar from './Sidebar';
import { Loading } from './States';
import { useAuth } from '../auth/AuthContext';

export default function Layout() {
  const { user, checking } = useAuth();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);

  if (checking) return <Loading label="Checking your session…" />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      <div className="hidden lg:block lg:w-64 shrink-0">
        <Sidebar />
      </div>
      {menuOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-slate-900/50" onClick={() => setMenuOpen(false)} />
          <div className="absolute inset-y-0 left-0 w-64">
            <button onClick={() => setMenuOpen(false)} className="absolute right-2 top-2 p-1 text-slate-500 z-10" aria-label="Close menu">
              <X className="w-5 h-5" />
            </button>
            <Sidebar onNavigate={() => setMenuOpen(false)} />
          </div>
        </div>
      )}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="lg:hidden flex items-center gap-2 bg-white border-b border-slate-200 px-3 py-2">
          <button onClick={() => setMenuOpen(true)} className="p-1 text-slate-600" aria-label="Open menu">
            <Menu className="w-5 h-5" />
          </button>
          <span className="font-bold text-sm">ScholarSetu console</span>
        </header>
        <main className="flex-1 overflow-y-auto">
          <div className="px-4 sm:px-6 lg:px-8 py-5 max-w-7xl mx-auto">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
