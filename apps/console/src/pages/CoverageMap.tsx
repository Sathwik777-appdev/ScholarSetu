import { useState } from 'react';
import { useApi } from '../hooks/useApi';
import { ApiView, Card, EmptyState, PageHeader } from '../components/States';
import { Towers3D } from '../components/Lazy3D';
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
              <button key={l} onClick={() => setLevel(l)} className={`px-3.5 py-1.5 rounded-full text-xs font-medium ring-1 transition ${level === l ? 'bg-ink-900 text-white ring-ink-900' : 'bg-white text-slate-700 ring-slate-200 hover:ring-slate-300'}`}>
                By {l}
              </button>
            ))}
          </div>
        } />
      <ApiView state={report} isEmpty={(r) => r.rows.length === 0} empty={<EmptyState title="No enrolment data for your jurisdiction" />}>
        {(r) => (
          <div className="space-y-3">
            <Card title={`Coverage by ${r.level}`} className="overflow-hidden">
              <Towers3D
                className="h-80 -mx-2 rounded-xl"
                scaleMax={100}
                label={`Coverage: ${r.rows.map((row) => `${row.block ?? row.district} ${row.coverage_pct.toFixed(1)}%`).join(', ')}`}
                data={[...r.rows].sort((a, b) => a.coverage_pct - b.coverage_pct).slice(0, 12).map((row) => ({
                  label: row.block ?? row.district, value: row.coverage_pct, display: pct(row.coverage_pct),
                  color: row.coverage_pct < 40 ? '#f43f5e' : row.coverage_pct < 70 ? '#f59e0b' : '#10b981',
                }))}
                fallback={<p className="text-sm text-slate-500">3D view unavailable on this device; the table below has the same figures.</p>}
              />
              <p className="mt-2 text-xs text-slate-400">Bar height is coverage out of 100%. Lowest first (up to 12); red below 40%, amber below 70%.</p>
            </Card>
            <Card>
              <p className="text-sm text-slate-700">Method: {r.method}</p>
              <p className="text-xs text-slate-500 mt-1">Linked by hashed APAAR ID: {r.matched_by_apaar} · by Bloom-filter encoding (CLK): {r.matched_by_clk}</p>
            </Card>
            <div className="rise bg-white border border-slate-200/70 rounded-2xl overflow-x-auto shadow-soft">
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
