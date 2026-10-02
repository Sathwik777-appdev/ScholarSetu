import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Search } from 'lucide-react';
import { useApi } from '../hooks/useApi';
import { ApiView, EmptyState, PageHeader } from '../components/States';
import StatusBadge from '../components/StatusBadge';
import { SCHEME_LABELS, STATE_LABELS, formatDays, schemeLabel } from '../utils/formatters';
import type { OfficerApplication } from '../types';

const PAGE = 50;
const control = 'select !py-2 !text-sm';

export default function Applications() {
  const [params, setParams] = useSearchParams();
  const state = params.get('state') ?? '';
  const scheme = params.get('scheme') ?? '';
  const openOnly = params.get('open') !== 'all';
  const [search, setSearch] = useState(params.get('q') ?? '');
  const [query, setQuery] = useState(search);
  const [offset, setOffset] = useState(0);

  useEffect(() => {  // search the whole jurisdiction on the server, not just the loaded page
    const t = window.setTimeout(() => { setQuery(search.trim()); setOffset(0); }, 300);
    return () => window.clearTimeout(t);
  }, [search]);

  const update = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value); else next.delete(key);
    setParams(next, { replace: true });
    setOffset(0);
  };
  const api = useApi<OfficerApplication[]>('/applications', {
    state: state || undefined, scheme: scheme || undefined, q: query || undefined,
    open_only: openOnly && !state ? 'true' : undefined, limit: PAGE, offset,
  });

  return (
    <div>
      <PageHeader title="Applications" subtitle="Every application in your area, longest in its current stage first." />
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <label className="text-[13px] font-medium text-slate-600">Stage
          <select value={state} onChange={(e) => update('state', e.target.value)} className={`${control} mt-1 block`}>
            <option value="">All stages</option>
            {Object.entries(STATE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </label>
        <label className="text-[13px] font-medium text-slate-600">Scheme
          <select value={scheme} onChange={(e) => update('scheme', e.target.value)} className={`${control} mt-1 block`}>
            <option value="">All schemes</option>
            {Object.entries(SCHEME_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </label>
        <label className="min-w-[14rem] flex-1 text-[13px] font-medium text-slate-600">Search
          <span className="relative mt-1 block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Student name or application ID"
              className={`${control} !pl-9`} />
          </span>
        </label>
        {!state && (
          <label className="flex items-center gap-2 pb-2 text-sm text-slate-700">
            <input type="checkbox" checked={openOnly} onChange={(e) => update('open', e.target.checked ? '' : 'all')} className="h-4 w-4 accent-amber-500" />
            Open only
          </label>
        )}
      </div>
      <ApiView state={api} isEmpty={(d) => d.length === 0 && offset === 0}
        empty={<EmptyState title="No applications" hint={query ? `Nothing in your area matches “${query}”.` : 'None in your area match these filters.'} />}>
        {(rows) => (
          <>
            <div className="rise card overflow-x-auto">
              <table className="table">
                <thead>
                  <tr><th>Student</th><th>Application</th>
                    <th>Scheme</th><th>Stage</th>
                    <th className="!text-right">In this stage</th></tr>
                </thead>
                <tbody>
                  {rows.map((a) => (
                    <tr key={a.id}>
                      <td><Link to={`/application/${a.id}`} className="font-semibold text-slate-900 hover:underline">{a.student_name}</Link>
                        <p className="text-[13px] text-slate-500">{a.district}, {a.state_name}</p></td>
                      <td className="font-mono text-[13px] text-slate-600">{a.id}</td>
                      <td>{schemeLabel(a.scheme)} <span className="text-[13px] text-slate-500">{a.academic_year}</span></td>
                      <td><StatusBadge status={a.canonical_state} /></td>
                      <td className="text-right tabular-nums">{formatDays(a.days_in_state)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-3 flex items-center justify-between text-sm">
              <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}
                className="btn btn-outline btn-sm">Previous</button>
              <span className="text-slate-500">{rows.length ? `${offset + 1}–${offset + rows.length}` : 'No more'}</span>
              <button disabled={rows.length < PAGE} onClick={() => setOffset(offset + PAGE)}
                className="btn btn-outline btn-sm">Next</button>
            </div>
          </>
        )}
      </ApiView>
    </div>
  );
}
