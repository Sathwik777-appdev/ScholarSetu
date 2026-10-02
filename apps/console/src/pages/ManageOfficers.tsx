import { useState, type FormEvent } from 'react';
import { CheckCircle2, Mail, UserPlus, UserX } from 'lucide-react';
import { apiClient, errorMessage } from '../api/client';
import { useApi } from '../hooks/useApi';
import { useAuth } from '../auth/auth';
import { ApiView, Card, EmptyState, PageHeader } from '../components/States';
import { ROLE_LABELS } from '../utils/formatters';
import type { UserRole } from '../types';

interface Officer {
  id: string;
  name: string;
  role: UserRole;
  email: string | null;
  phone: string | null;
  jurisdiction_state: string | null;
  jurisdiction_district: string | null;
  institution_code: string | null;
  is_active: boolean;
  is_demo: boolean;
}

const ROLES: { role: UserRole; hint: string }[] = [
  { role: 'INSTITUTE_OFFICER', hint: 'Verifies applications from one school or college' },
  { role: 'DISTRICT_OFFICER', hint: 'Sanctions and raises deficiencies in one district' },
  { role: 'STATE_OFFICER', hint: 'Oversees every district of one state' },
  { role: 'MINISTRY', hint: 'All India, and can enrol officers' },
];

const field = 'mt-1.5 w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-[15px] shadow-sm outline-none transition focus:border-saffron-500 focus:ring-4 focus:ring-saffron-400/20';
const label = 'block text-sm font-medium text-slate-700';

function EnrolForm({ onDone }: { onDone: () => void }) {
  const [role, setRole] = useState<UserRole | ''>('');
  const [form, setForm] = useState({ name: '', email: '', phone: '', state: '', district: '', code: '' });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const needsState = role !== '' && role !== 'MINISTRY';
  const needsDistrict = role === 'DISTRICT_OFFICER' || role === 'INSTITUTE_OFFICER';

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true); setError(null); setDone(null);
    try {
      await apiClient.post('/admin/officers', {
        name: form.name.trim(), email: form.email.trim(), role,
        ...(form.phone.trim() ? { phone: form.phone.trim() } : {}),
        ...(needsState ? { jurisdiction_state: form.state.trim() } : {}),
        ...(needsDistrict ? { jurisdiction_district: form.district.trim() } : {}),
        ...(role === 'INSTITUTE_OFFICER' && form.code.trim() ? { institution_code: form.code.trim() } : {}),
      });
      setDone(`${form.name.trim()} can now sign in with a code emailed to ${form.email.trim().toLowerCase()}.`);
      setForm({ name: '', email: '', phone: '', state: '', district: '', code: '' });
      setRole('');
      onDone();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="space-y-5">
      <fieldset>
        <legend className={label}>Role</legend>
        <div className="mt-2 grid gap-2 sm:grid-cols-2">
          {ROLES.map((r) => (
            <label key={r.role} className={`flex cursor-pointer items-start gap-3 rounded-xl border p-3 transition ${
              role === r.role ? 'border-saffron-500 bg-saffron-500/5 ring-2 ring-saffron-400/30' : 'border-slate-200 hover:border-slate-300'}`}>
              <input type="radio" name="role" value={r.role} checked={role === r.role} onChange={() => setRole(r.role)} className="mt-1 accent-amber-500" />
              <span>
                <span className="block text-sm font-semibold text-slate-900">{ROLE_LABELS[r.role]}</span>
                <span className="block text-[13px] text-slate-500">{r.hint}</span>
              </span>
            </label>
          ))}
        </div>
      </fieldset>
      <div className="grid gap-4 sm:grid-cols-2">
        <label className={label}>Full name or post
          <input required minLength={2} maxLength={100} value={form.name} onChange={set('name')} className={field}
            placeholder="District Welfare Officer, Jama" />
        </label>
        <label className={label}>Official email (used to sign in)
          <input required type="email" value={form.email} onChange={set('email')} className={field} placeholder="name@tribal.gov.in" />
        </label>
        <label className={label}>Mobile number (optional)
          <input inputMode="numeric" pattern="[0-9]{10}" value={form.phone} onChange={set('phone')} className={field} placeholder="10 digits" />
        </label>
        {needsState && (
          <label className={label}>State
            <input required value={form.state} onChange={set('state')} className={field} placeholder="Jharkhand" />
          </label>
        )}
        {needsDistrict && (
          <label className={label}>District
            <input required value={form.district} onChange={set('district')} className={field} placeholder="Dumka" />
          </label>
        )}
        {role === 'INSTITUTE_OFFICER' && (
          <label className={label}>Institution code (AISHE or UDISE+, optional)
            <input value={form.code} onChange={set('code')} className={field} placeholder="C-41290" />
          </label>
        )}
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
        <p className="text-[13px] text-slate-500">Enrolled officers sign in with an emailed code. They never accept the demo code.</p>
        <button disabled={busy || role === ''} className="inline-flex items-center gap-2 rounded-xl bg-ink-900 px-4 py-2.5 text-sm font-semibold text-white shadow-lift hover:bg-ink-800 disabled:opacity-50">
          <UserPlus className="h-4 w-4" /> {busy ? 'Enrolling…' : 'Enrol officer'}
        </button>
      </div>
      {error && <p role="alert" className="rounded-xl bg-rose-50 p-3 text-sm text-rose-800 ring-1 ring-rose-200">{error}</p>}
      {done && <p className="flex items-center gap-2 rounded-xl bg-emerald-50 p-3 text-sm text-emerald-800 ring-1 ring-emerald-200"><CheckCircle2 className="h-4 w-4" />{done}</p>}
    </form>
  );
}

export default function ManageOfficers() {
  const officers = useApi<Officer[]>('/admin/officers');
  const { user } = useAuth();
  const [error, setError] = useState<string | null>(null);

  const toggle = async (o: Officer) => {
    if (o.is_active && !window.confirm(`Deactivate ${o.name}? They will be signed out and cannot sign in.`)) return;
    setError(null);
    try {
      await apiClient.post(`/admin/officers/${o.id}/active`, { active: !o.is_active });
      officers.reload();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader title="Officers" subtitle="Enrol officers, see who can sign in, and switch accounts off when people move on." />
      <Card title="Enrol an officer"><EnrolForm onDone={officers.reload} /></Card>
      <Card title="Officer accounts">
        {error && <p role="alert" className="mb-3 rounded-xl bg-rose-50 p-3 text-sm text-rose-800 ring-1 ring-rose-200">{error}</p>}
        <ApiView state={officers} isEmpty={(d) => d.length === 0} empty={<EmptyState title="No officers yet" />}>
          {(rows) => (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-[12px] uppercase tracking-wide text-slate-500">
                    <th className="py-2 pr-3 font-semibold">Officer</th>
                    <th className="py-2 pr-3 font-semibold">Role</th>
                    <th className="py-2 pr-3 font-semibold">Jurisdiction</th>
                    <th className="py-2 pr-3 font-semibold">Status</th>
                    <th className="py-2" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {rows.map((o) => (
                    <tr key={o.id} className={o.is_active ? '' : 'text-slate-400'}>
                      <td className="py-3 pr-3">
                        <p className="font-medium text-slate-900">{o.name}</p>
                        <p className="flex items-center gap-1 text-[13px] text-slate-500"><Mail className="h-3.5 w-3.5" />{o.email ?? o.phone}</p>
                      </td>
                      <td className="py-3 pr-3">{ROLE_LABELS[o.role] ?? o.role}</td>
                      <td className="py-3 pr-3">{o.role === 'MINISTRY' ? 'All India'
                        : [o.jurisdiction_district, o.jurisdiction_state].filter(Boolean).join(', ')}</td>
                      <td className="py-3 pr-3">
                        <span className={`rounded-full px-2 py-0.5 text-[12px] font-semibold ${o.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>
                          {o.is_active ? 'Active' : 'Deactivated'}</span>
                        {o.is_demo && <span className="ml-1.5 rounded-full bg-saffron-500/10 px-2 py-0.5 text-[12px] font-semibold text-amber-800">Demo</span>}
                      </td>
                      <td className="py-3 text-right">
                        {o.id !== user?.id && (
                          <button onClick={() => toggle(o)} className="inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-[13px] font-medium text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50">
                            <UserX className="h-3.5 w-3.5" />{o.is_active ? 'Deactivate' : 'Reactivate'}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </ApiView>
      </Card>
    </div>
  );
}
