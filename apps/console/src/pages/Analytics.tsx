import { useApi } from '../hooks/useApi';
import { ApiView, Card, EmptyState, PageHeader } from '../components/States';
import { schemeLabel, stateLabel } from '../utils/formatters';
import type { BottleneckRow, TransitionRow } from '../types';

export default function Analytics() {
  const bottlenecks = useApi<BottleneckRow[]>('/analytics/bottlenecks');
  const transitions = useApi<TransitionRow[]>('/analytics/transitions');

  return (
    <div className="space-y-4">
      <PageHeader title="Bottlenecks and SLA" subtitle="Where open applications wait, and whether students move on to the next scheme." />
      <Card title="Where applications wait (open applications, from the ledger)">
        <ApiView state={bottlenecks} isEmpty={(d) => d.length === 0} empty={<EmptyState title="No open applications" />}>
          {(rows) => (
            <table className="w-full text-sm">
              <thead className="text-xs text-slate-500 text-left"><tr><th className="py-1">District</th><th>Stage</th><th className="text-right">Open</th><th className="text-right">Avg days in stage</th><th className="text-right">Past SLA</th></tr></thead>
              <tbody className="divide-y divide-slate-100">
                {rows.map((r) => (
                  <tr key={`${r.state_name}-${r.district}-${r.stage}`}>
                    <td className="py-1.5">{r.district}, {r.state_name}</td><td>{stateLabel(r.stage)}</td>
                    <td className="text-right tabular-nums">{r.open_applications}</td>
                    <td className="text-right tabular-nums">{r.avg_days_in_stage.toFixed(1)}</td>
                    <td className={`text-right tabular-nums ${r.sla_breaches ? 'text-rose-700 font-semibold' : ''}`}>{r.sla_breaches}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </ApiView>
      </Card>
      <Card title="Scheme transitions (e.g. Pre-Matric → Post-Matric)">
        <ApiView state={transitions} isEmpty={(d) => d.length === 0} empty={<EmptyState title="No transition cohort yet" hint="Needs scholarship holders from the previous academic year." />}>
          {(rows) => (
            <table className="w-full text-sm">
              <thead className="text-xs text-slate-500 text-left"><tr><th className="py-1">District</th><th>From → to</th><th>Years</th><th className="text-right">Cohort</th><th className="text-right">Applied</th><th className="text-right">Conversion</th></tr></thead>
              <tbody className="divide-y divide-slate-100">
                {rows.map((r) => (
                  <tr key={`${r.district}-${r.from_scheme}-${r.to_scheme}`}>
                    <td className="py-1.5">{r.district}</td><td>{schemeLabel(r.from_scheme)} → {schemeLabel(r.to_scheme)}</td>
                    <td>{r.previous_year} → {r.current_year}</td>
                    <td className="text-right tabular-nums">{r.eligible_cohort}</td><td className="text-right tabular-nums">{r.applied}</td>
                    <td className="text-right tabular-nums">{r.conversion_pct === null ? '—' : `${r.conversion_pct.toFixed(1)}%`}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </ApiView>
      </Card>
    </div>
  );
}
