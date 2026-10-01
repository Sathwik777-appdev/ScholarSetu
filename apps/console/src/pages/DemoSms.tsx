import { useApi } from '../hooks/useApi';
import { ApiView, Card, EmptyState, PageHeader } from '../components/States';
import { formatDateTime, humanize } from '../utils/formatters';

interface Sms { created_at: string; to_phone: string; category: string; body: string }

/** Demo mode only, Ministry only: the simulated SMS gateway's messages, so self-registration can be shown live.
 * The public outbox page shows only the seeded demo accounts. */
export default function DemoSms() {
  const sms = useApi<Sms[]>('/dev/sms-outbox/all');
  return (
    <div className="space-y-4">
      <PageHeader title="Simulated SMS (demo)" subtitle="Every message the demo's simulated gateway would have sent. Each view is audited." />
      <ApiView state={sms} isEmpty={(d) => d.length === 0} empty={<EmptyState title="No messages yet" />}>
        {(rows) => (
          <Card>
            <ul className="divide-y divide-slate-100">
              {rows.map((m, i) => (
                <li key={i} className="py-2 text-sm">
                  <p className="text-xs text-slate-500">{formatDateTime(m.created_at)} · {m.to_phone} · {humanize(m.category)}</p>
                  <p>{m.body}</p>
                </li>
              ))}
            </ul>
          </Card>
        )}
      </ApiView>
      <button onClick={sms.reload} className="rounded-lg px-3 py-2 text-sm border border-slate-300">Refresh</button>
    </div>
  );
}
