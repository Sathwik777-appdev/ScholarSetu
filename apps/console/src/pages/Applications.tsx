import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { ApiView, EmptyState, PageHeader } from '../components/States';
import StatusBadge from '../components/StatusBadge';
import { SCHEME_LABELS, STATE_LABELS, formatDays, schemeLabel } from '../utils/formatters';
import type { OfficerApplication } from '../types';

const PAGE = 50;

export default function Applications() {
  const [state, setState] = useState('');
  const [scheme, setScheme] = useState('');
  const [search, setSearch] = useState('');
  const [offset, setOffset] = useState(0);
  const api = useApi<OfficerApplication[]>('/applications', {
    state: state || undefined, scheme: scheme || undefined, limit: PAGE, offset,
  });
  const q = search.trim().toLowerCase();

  return (
    <div>
      <PageHeader title="Applications" subtitle="Every application in your jurisdiction, longest waiting first." />
      <div className="flex flex-wrap gap-2 mb-4 text-sm">
        <select value={state} onChange={(e) => { setState(e.target.value); setOffset(0); }} className="border border-slate-300 rounded px-2 py-1 bg-white">
          <option value="">All stages</option>
          {Object.entries(STATE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select value={scheme} onChange={(e) => { setScheme(e.target.value); setOffset(0); }} className="border border-slate-300 rounded px-2 py-1 bg-white">
          <option value="">All schemes</option>
          {Object.entries(SCHEME_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Filter this page by name or ID"
          className="border border-slate-300 rounded px-2 py-1 flex-1 min-w-[12rem]" />
      </div>
      <ApiView state={api} isEmpty={(d) => d.length === 0 && offset === 0}
        empty={<EmptyState title="No applications" hint="None in your jurisdiction match these filters." />}>
        {(rows) => {
          const shown = rows.filter((r) => !q || r.student_name.toLowerCase().includes(q) || r.id.toLowerCase().includes(q));
          return (
            <>
              <div className="rise bg-white border border-slate-200/70 rounded-2xl overflow-x-auto shadow-soft">
                <table className="min-w-full text-sm">
                  <thead className="bg-slate-50 text-xs uppercase text-slate-500 text-left">
                    <tr><th className="p-3">Application</th><th className="p-3">Student</th><th className="p-3">Scheme</th><th className="p-3">Stage</th><th className="p-3 text-right">In this stage</th></tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {shown.map((a) => (
                      <tr key={a.id} className="hover:bg-slate-50">
                        <td className="p-3 font-mono text-xs"><Link className="text-blue-800 underline" to={`/application/${a.id}`}>{a.id}</Link></td>
                        <td className="p-3"><p className="font-semibold">{a.student_name}</p><p className="text-xs text-slate-500">{a.district}, {a.state_name}</p></td>
                        <td className="p-3">{schemeLabel(a.scheme)} <span className="text-xs text-slate-500">{a.academic_year}</span></td>
                        <td className="p-3"><StatusBadge status={a.canonical_state} /></td>
                        <td className="p-3 text-right tabular-nums">{formatDays(a.days_in_state)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {shown.length === 0 && <p className="p-4 text-sm text-slate-500">No application on this page matches “{search}”.</p>}
              </div>
              <div className="flex items-center justify-between mt-3 text-xs">
                <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))} className="px-3 py-1 border rounded disabled:opacity-40">Previous</button>
                <span className="text-slate-500">Showing {offset + 1}–{offset + rows.length}</span>
                <button disabled={rows.length < PAGE} onClick={() => setOffset(offset + PAGE)} className="px-3 py-1 border rounded disabled:opacity-40">Next</button>
              </div>
            </>
          );
        }}
      </ApiView>
    </div>
  );
}
