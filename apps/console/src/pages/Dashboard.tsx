import { Link } from 'react-router-dom';
import { AlertTriangle, ClipboardCheck, FileText, IndianRupee, Users } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useApi } from '../hooks/useApi';
import { ApiView, Card, EmptyState, PageHeader } from '../components/States';
import StatCard from '../components/StatCard';
import { useDemoMode } from '../auth/demo';
import StatusBadge from '../components/StatusBadge';
import { formatCurrency, formatDays, schemeLabel, stateLabel } from '../utils/formatters';
import type { AnalyticsOverview, SLARow } from '../types';

const STAGE_COLOR: Record<string, string> = {
  SUBMITTED: '#3b82f6', INSTITUTE_VERIFICATION: '#f59e0b', DEFICIENCY_RAISED: '#f43f5e', RESUBMITTED: '#fb923c',
  AUTHORITY_VERIFICATION: '#8b5cf6', SANCTIONED: '#6366f1', REJECTED: '#be123c', PAYMENT_INITIATED: '#14b8a6',
  CREDITED: '#10b981', PAYMENT_FAILED: '#e11d48', RENEWAL_DUE: '#ec4899', DRAFT: '#94a3b8',
};

export default function Dashboard() {
  const overview = useApi<AnalyticsOverview>('/analytics/overview');
  const sla = useApi<SLARow[]>('/analytics/sla');
  const demo = useDemoMode();

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
                    hint={`${o.total_students.toLocaleString('en-IN')} student${o.total_students === 1 ? '' : 's'}`} />
                  <StatCard name="Credited" value={formatCurrency(o.credited_amount)} icon={IndianRupee} tone="good"
                    hint={`of ${formatCurrency(o.sanctioned_amount)} sanctioned`} />
                  <StatCard name="Failed payments" value={o.payments_failed} icon={AlertTriangle} tone={o.payments_failed ? 'bad' : 'default'}
                    hint={`${formatCurrency(o.failed_amount)} not landed · ${o.payments_total} payments in all`} />
                  <StatCard name="Open review cases" value={o.open_review_cases} icon={ClipboardCheck}
                    tone={o.open_review_cases ? 'bad' : 'default'} hint="claims waiting for an officer's decision" />
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  <Card title="Applications by stage">
                    <div style={{ height: Math.max(160, o.by_state.length * 44) }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={[...o.by_state].sort((a, b) => b.count - a.count).map((r) => ({ key: r.key, name: stateLabel(r.key), count: r.count }))}
                          layout="vertical" margin={{ left: 8, right: 48, top: 4, bottom: 4 }}>
                          <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
                          <XAxis type="number" allowDecimals={false} fontSize={12} stroke="#94a3b8" />
                          <YAxis type="category" dataKey="name" width={150} fontSize={13} stroke="#475569" tickLine={false} />
                          <Tooltip cursor={{ fill: '#f1f5f9' }} />
                          <Bar dataKey="count" name="Applications" radius={[0, 6, 6, 0]} barSize={22} animationDuration={400}>
                            {[...o.by_state].sort((a, b) => b.count - a.count).map((r) => <Cell key={r.key} fill={STAGE_COLOR[r.key] ?? '#64748b'} />)}
                            <LabelList dataKey="count" position="right" fontSize={13} fill="#0f172a" />
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </Card>
                  <Card title="By scheme">
                    <table className="w-full text-sm">
                      <thead className="text-[12px] uppercase tracking-wide text-slate-500 text-left"><tr><th className="py-1">Scheme</th><th className="text-right">Applications</th><th className="text-right">Sanctioned</th><th className="text-right">Credited</th></tr></thead>
                      <tbody className="divide-y divide-slate-100">
                        {o.by_scheme.map((s) => (
                          <tr key={s.scheme}><td className="py-1.5">{schemeLabel(s.scheme)}</td><td className="text-right tabular-nums">{s.applications}</td>
                            <td className="text-right tabular-nums">{formatCurrency(s.sanctioned)}</td><td className="text-right tabular-nums">{formatCurrency(s.credited)}</td></tr>
                        ))}
                      </tbody>
                    </table>
                    <div className="mt-5 space-y-3">
                      {o.by_scheme.filter((x) => Number(x.sanctioned) > 0).map((x) => {
                        const pct = Math.round((Number(x.credited) / Number(x.sanctioned)) * 100);
                        return (
                          <div key={x.scheme}>
                            <div className="flex justify-between text-[13px] text-slate-600"><span>{schemeLabel(x.scheme)}: credited of sanctioned</span><span className="tabular-nums">{pct}%</span></div>
                            <div className="mt-1 h-2 rounded-full bg-slate-100"><div className="h-2 rounded-full bg-teal-500" style={{ width: `${pct}%` }} /></div>
                          </div>
                        );
                      })}
                    </div>
                    <p className="mt-4 flex items-center gap-1 text-[13px] text-slate-500"><Users className="h-3.5 w-3.5" /> Amounts are sums of ledger payment records.</p>
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
              <thead className="text-[12px] uppercase tracking-wide text-slate-500 text-left"><tr><th className="py-1">Application</th><th>District</th><th>Stage</th><th className="text-right">Waiting / target</th></tr></thead>
              <tbody className="divide-y divide-slate-100">
                {rows.filter((r) => r.breached).slice(0, 10).map((r) => (
                  <tr key={r.application_id}>
                    <td className="py-1.5 font-mono text-[13px]"><Link className="text-blue-800 underline" to={`/application/${r.application_id}`}>{r.application_id}</Link></td>
                    <td>{r.district}</td><td><StatusBadge status={r.state} /></td>
                    <td className="text-right tabular-nums">{formatDays(r.days_in_state)} / {formatDays(r.sla_days)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </ApiView>
        <p className="mt-2 text-[13px] text-slate-500">
          {demo.info?.available
            ? 'Demo timers: each stage target is shortened so that delays and escalations can be shown live. '
            : ''}
          SLA targets are set per stage; they are not official service norms.</p>
      </Card>
    </div>
  );
}
