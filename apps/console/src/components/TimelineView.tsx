import { TimelineEvent } from '../types';
import { formatDate } from '../utils/formatters';
import { ShieldCheck, CheckCircle2, Lock, UserCheck, Sparkles, Send, FileCheck } from 'lucide-react';

interface TimelineViewProps {
  events: TimelineEvent[];
}

export default function TimelineView({ events }: TimelineViewProps) {
  const getEventBadge = (type: string) => {
    switch (type) {
      case 'INDIC_IDENTITY_MATCH':
        return {
          icon: Sparkles,
          bg: 'bg-indigo-600 text-white',
          label: 'Indic Phonetic Match',
          chip: 'bg-indigo-50 text-indigo-700 border-indigo-200',
        };
      case 'PASSPORT_ATTESTATION_REUSE':
        return {
          icon: ShieldCheck,
          bg: 'bg-emerald-600 text-white',
          label: 'Ed25519 Attestation Reused',
          chip: 'bg-emerald-50 text-emerald-700 border-emerald-200',
        };
      case 'PATHWAY_NUDGE_CLAIM':
        return {
          icon: Send,
          bg: 'bg-blue-600 text-white',
          label: 'Pathway Nudge 1-Tap Claim',
          chip: 'bg-blue-50 text-blue-700 border-blue-200',
        };
      case 'VERIFICATION':
        return {
          icon: CheckCircle2,
          bg: 'bg-emerald-500 text-white',
          label: 'Institutional Verification',
          chip: 'bg-slate-100 text-slate-700 border-slate-200',
        };
      default:
        return {
          icon: FileCheck,
          bg: 'bg-slate-600 text-white',
          label: type,
          chip: 'bg-slate-100 text-slate-600 border-slate-200',
        };
    }
  };

  return (
    <div className="flow-root">
      <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-100 text-xs">
        <span className="font-bold text-slate-700 flex items-center gap-1.5">
          <Lock className="w-3.5 h-3.5 text-emerald-600" />
          <span>Tamper-Evident SHA-256 Hash Chain</span>
        </span>
        <span className="font-mono text-[11px] text-slate-400">Block Height: #{events.length}</span>
      </div>

      <ul role="list" className="-mb-8">
        {events.map((event, eventIdx) => {
          const badge = getEventBadge(event.event_type);
          const Icon = badge.icon;

          return (
            <li key={event.event_id}>
              <div className="relative pb-8">
                {eventIdx !== events.length - 1 ? (
                  <span className="absolute left-5 top-5 -ml-px h-full w-0.5 bg-slate-200" aria-hidden="true" />
                ) : null}
                <div className="relative flex items-start space-x-3.5">
                  <div>
                    <span className={`h-10 w-10 rounded-2xl flex items-center justify-center ring-4 ring-white shadow-2xs ${badge.bg}`}>
                      <Icon className="h-5 w-5" />
                    </span>
                  </div>
                  <div className="flex min-w-0 flex-1 justify-between gap-x-4 pt-1">
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-bold text-slate-900">{event.actor}</span>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${badge.chip}`}>
                          {badge.label}
                        </span>
                      </div>
                      <p className="text-xs text-slate-600 leading-relaxed max-w-xl">
                        {event.description}
                      </p>
                    </div>
                    <div className="whitespace-nowrap text-right text-[11px] font-mono text-slate-400">
                      <time dateTime={event.occurred_at}>{formatDate(event.occurred_at)}</time>
                    </div>
                  </div>
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
