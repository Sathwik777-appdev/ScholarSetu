import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ShieldOff } from 'lucide-react';
import { useAuth } from '../auth/auth';
import type { UserRole } from '../types';
import { ROLE_LABELS } from '../utils/formatters';

/** The page for a signed-in person whose role the API would refuse, instead of a failed data load. The API still
 * enforces every rule; this only says so plainly. */
export function NoAccess({ role }: { role?: UserRole }) {
  return (
    <div className="rise mx-auto mt-10 max-w-md rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-soft">
      <span className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-2xl bg-slate-100"><ShieldOff className="h-6 w-6 text-slate-500" /></span>
      <h1 className="text-lg font-semibold text-slate-900">This page is not part of your role</h1>
      <p className="mt-2 text-sm text-slate-600">
        {role ? `${ROLE_LABELS[role] ?? role} accounts cannot open it. ` : ''}If you need it, ask the Ministry administrator
        to change your role.
      </p>
      <Link to="/my-work" className="btn btn-primary mt-5">Back to my work</Link>
    </div>
  );
}

export default function RequireRole({ roles, children }: { roles: UserRole[]; children: ReactNode }) {
  const { user } = useAuth();
  if (!user || roles.includes(user.role)) return <>{children}</>;
  return <NoAccess role={user.role} />;
}
