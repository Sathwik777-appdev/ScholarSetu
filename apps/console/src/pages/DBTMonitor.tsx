import { useApi } from '../hooks/useApi';
import { ApiView, Card, EmptyState, PageHeader } from '../components/States';
import { formatCurrency, humanize } from '../utils/formatters';
import type { AnalyticsOverview, DBTHotspotRow } from '../types';

export default function DBTMonitor() {
  const hotspots = useApi<DBTHotspotRow[]>('/analytics/dbt-failures');
  const overview = useApi<AnalyticsOverview>('/analytics/overview');

  return (
    <div className="space-y-4">
      <PageHeader title="DBT failures" subtitle="Districts where DBT Guardian bank checks found that money would not land, for targeted bank camps." />
      <Card title="Payments in your jurisdiction">
        <ApiView state={overview}>
          {(o) => (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
              <div><p className="text-xs text-slate-500">Sanctioned</p><p className="font-bold">{formatCurrency(o.sanctioned_amount)}</p></div>
              <div><p className="text-xs text-slate-500">Credited</p><p className="font-bold text-emerald-800">{formatCurrency(o.credited_amount)}</p></div>
              <div><p className="text-xs text-slate-500">In progress</p><p className="font-bold">{formatCurrency(o.pending_amount)}</p></div>
              <div><p className="text-xs text-slate-500">Failed</p><p className="font-bold text-rose-700">{formatCurrency(o.failed_amount)} ({o.payments_failed})</p></div>
            </div>
          )}
        </ApiView>
      </Card>
      <Card title="Bank-readiness problems by district (latest DBT Guardian check per application)">
        <ApiView state={hotspots} isEmpty={(d) => d.length === 0} empty={<EmptyState title="No bank checks have been run yet" />}>
          {(rows) => (
            <table className="w-full text-sm">
              <thead className="text-xs text-slate-500 text-left"><tr><th className="py-1">District</th><th className="text-right">Checked</th><th className="text-right">Failing</th><th className="text-right">Rate</th><th>Issues</th></tr></thead>
              <tbody className="divide-y divide-slate-100">
                {[...rows].sort((a, b) => b.failure_rate_pct - a.failure_rate_pct).map((r) => (
                  <tr key={r.district}>
                    <td className="py-1.5">{r.district}</td>
                    <td className="text-right tabular-nums">{r.applications_checked}</td>
                    <td className="text-right tabular-nums">{r.failing}</td>
                    <td className="text-right tabular-nums">{r.failure_rate_pct.toFixed(1)}%</td>
                    <td className="text-xs">{Object.entries(r.issue_counts).map(([k, v]) => `${humanize(k)} (${v})`).join(', ') || '—'}</td>
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
