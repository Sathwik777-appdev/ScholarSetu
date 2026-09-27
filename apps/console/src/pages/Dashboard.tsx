import { Link } from 'react-router-dom';
import { AlertTriangle, ClipboardCheck, FileText, IndianRupee, Users } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useApi } from '../hooks/useApi';
import { ApiView, Card, EmptyState, PageHeader } from '../components/States';
import StatCard from '../components/StatCard';
import StatusBadge from '../components/StatusBadge';
import { formatCurrency, schemeLabel, stateLabel } from '../utils/formatters';
import type { AnalyticsOverview, SLARow } from '../types';

export default function Dashboard() {
  const overview = useApi<AnalyticsOverview>('/analytics/overview');
  const sla = useApi<SLARow[]>('/analytics/sla');

  return (
    <div className="space-y-5">
      <ApiView state={overview}>
        {(o) => (
          <>
            <PageHeader title="Dashboard" subtitle={`${o.scope} · computed from the ledger when this page loaded`} />
            {o.total_applications === 0 ? (
              <EmptyState title="No applications in your jurisdiction yet" />
            ) : (
              <>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                  <StatCard name="Applications" value={o.total_applications.toLocaleString('en-IN')} icon={FileText}
                    hint={`${o.total_students.toLocaleString('en-IN')} students`} />
                  <StatCard name="Credited" value={formatCurrency(o.credited_amount)} icon={IndianRupee} tone="good"
                    hint={`of ${formatCurrency(o.sanctioned_amount)} sanctioned`} />
                  <StatCard name="Failed payments" value={o.payments_failed} icon={AlertTriangle} tone={o.payments_failed ? 'bad' : 'default'}
                    hint={`${formatCurrency(o.failed_amount)} not landed · ${o.payments_total} payments in all`} />
                  <StatCard name="Open review cases" value={o.open_review_cases} icon={ClipboardCheck}
                    hint={`${o.open_sla_breaches} applications past their SLA`} />
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  <Card title="Applications by stage">
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={o.by_state.map((r) => ({ name: stateLabel(r.key), count: r.count }))} layout="vertical" margin={{ left: 40 }}>
                          <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                          <XAxis type="number" allowDecimals={false} fontSize={11} />
                          <YAxis type="category" dataKey="name" width={150} fontSize={11} />
                          <Tooltip />
                          <Bar dataKey="count" name="Applications" fill="#1e293b" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </Card>
                  <Card title="By scheme">
                    <table className="w-full text-sm">
                      <thead className="text-xs text-slate-500 text-left"><tr><th className="py-1">Scheme</th><th className="text-right">Applications</th><th className="text-right">Sanctioned</th><th className="text-right">Credited</th></tr></thead>
                      <tbody className="divide-y divide-slate-100">
                        {o.by_scheme.map((s) => (
                          <tr key={s.scheme}><td className="py-1.5">{schemeLabel(s.scheme)}</td><td className="text-right tabular-nums">{s.applications}</td>
                            <td className="text-right tabular-nums">{formatCurrency(s.sanctioned)}</td><td className="text-right tabular-nums">{formatCurrency(s.credited)}</td></tr>
                        ))}
                      </tbody>
                    </table>
                    <p className="text-xs text-slate-500 mt-2 flex items-center gap-1"><Users className="w-3 h-3" /> Amounts are sums of ledger payment records.</p>
                  </Card>
                </div>
              </>
            )}
          </>
        )}
      </ApiView>

      <Card title="Longest past their SLA">
        <ApiView state={sla} isEmpty={(rows) => !rows.some((r) => r.breached)}
          empty={<p className="text-sm text-slate-500">No open application is past its SLA.</p>}>
          {(rows) => (
            <table className="w-full text-sm">
              <thead className="text-xs text-slate-500 text-left"><tr><th className="py-1">Application</th><th>District</th><th>Stage</th><th className="text-right">Days / SLA</th></tr></thead>
              <tbody className="divide-y divide-slate-100">
                {rows.filter((r) => r.breached).slice(0, 10).map((r) => (
                  <tr key={r.application_id}>
                    <td className="py-1.5 font-mono text-xs"><Link className="text-blue-800 underline" to={`/application/${r.application_id}`}>{r.application_id}</Link></td>
                    <td>{r.district}</td><td><StatusBadge status={r.state} /></td>
                    <td className="text-right tabular-nums">{r.days_in_state} / {r.sla_days}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </ApiView>
        <p className="text-xs text-slate-500 mt-2">SLA targets are configured per stage (SLA_DAYS_*); they are not official service norms.</p>
      </Card>
    </div>
  );
}
