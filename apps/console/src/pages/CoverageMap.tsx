import { useState } from 'react';
import { useApi } from '../hooks/useApi';
import { ApiView, Card, EmptyState, PageHeader } from '../components/States';
import type { CoverageReport } from '../types';

function pct(v: number | null) {
  return v === null ? '—' : `${v.toFixed(1)}%`;
}

export default function CoverageMap() {
  const [level, setLevel] = useState<'district' | 'block'>('district');
  const report = useApi<CoverageReport>('/analytics/coverage', { level });

  return (
    <div>
      <PageHeader title="Coverage (Reach Radar)"
        subtitle="Enrolled ST students (UDISE+) who hold a scholarship, found by privacy-preserving record linkage."
        actions={
          <div className="flex gap-1 text-xs">
            {(['district', 'block'] as const).map((l) => (
              <button key={l} onClick={() => setLevel(l)} className={`px-3 py-1 rounded border ${level === l ? 'bg-slate-900 text-white' : 'bg-white'}`}>
                By {l}
              </button>
            ))}
          </div>
        } />
      <ApiView state={report} isEmpty={(r) => r.rows.length === 0} empty={<EmptyState title="No enrolment data for your jurisdiction" />}>
        {(r) => (
          <div className="space-y-3">
            <Card>
              <p className="text-sm text-slate-700">Method: {r.method}</p>
              <p className="text-xs text-slate-500 mt-1">Linked by hashed APAAR ID: {r.matched_by_apaar} · by Bloom-filter encoding (CLK): {r.matched_by_clk}</p>
            </Card>
            <div className="bg-white border border-slate-200 rounded-lg overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-500 text-left">
                  <tr><th className="p-3">District</th>{r.level === 'block' && <th className="p-3">Block</th>}<th className="p-3 text-right">Enrolled ST</th>
                    <th className="p-3 text-right">With scholarship</th><th className="p-3 text-right">Coverage</th><th className="p-3 text-right">PVTG coverage</th></tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {[...r.rows].sort((a, b) => a.coverage_pct - b.coverage_pct).map((row) => (
                    <tr key={`${row.district}-${row.block}`}>
                      <td className="p-3">{row.district}</td>{r.level === 'block' && <td className="p-3">{row.block}</td>}
                      <td className="p-3 text-right tabular-nums">{row.enrolled_st}</td>
                      <td className="p-3 text-right tabular-nums">{row.with_scholarship}</td>
                      <td className="p-3 text-right tabular-nums">
                        <div className="flex items-center justify-end gap-2">
                          <div className="w-20 h-1.5 bg-slate-100 rounded"><div className="h-1.5 bg-slate-700 rounded" style={{ width: `${Math.min(100, row.coverage_pct)}%` }} /></div>
                          {pct(row.coverage_pct)}
                        </div>
                      </td>
                      <td className="p-3 text-right tabular-nums">{pct(row.pvtg_coverage_pct)} <span className="text-xs text-slate-500">({row.pvtg_with_scholarship}/{row.pvtg_enrolled})</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-xs text-slate-500">Lowest coverage first. The enrolment roster in this prototype is synthetic mock data.</p>
          </div>
        )}
      </ApiView>
    </div>
  );
}
