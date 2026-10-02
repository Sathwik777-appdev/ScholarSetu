import { formatCurrency, humanize, schemeLabel, stateLabel } from './formatters';

type Payload = Record<string, unknown>;
const str = (v: unknown) => (typeof v === 'string' ? v : v == null ? '' : String(v));
const money = (v: unknown) => (typeof v === 'number' ? formatCurrency(v) : '');

/** Who did it, in words: "District welfare officer", "Student", "NSP (portal sync)". */
export function describeActor(actor: string, source: string): string {
  if (actor.startsWith('user:')) return humanize(actor.split(':')[2] ?? 'officer');
  if (actor.startsWith('system:seed')) return 'Set up for the demo';
  if (actor.startsWith('system:')) return `ScholarSetu (${humanize(actor.slice(7))})`;
  if (source && source !== 'SCHOLARSETU') return `${source} (portal sync)`;
  return humanize(actor);
}

/** One ledger event as a sentence an officer can read. The raw record stays available for audit. */
export function describeEvent(type: string, p: Payload): string {
  switch (type) {
    case 'ApplicationCreated':
      return `Application created for ${schemeLabel(str(p.scheme))} ${str(p.academic_year)}`
        + (p.initial_state === 'DRAFT' ? ' as a draft.' : ' and submitted.');
    case 'ApplicationSubmitted': return 'The student submitted the application.';
    case 'InstituteVerificationStarted': return 'The institute started verifying the application.';
    case 'AuthorityVerificationStarted': return 'Forwarded to the district or state authority for verification.';
    case 'DeficiencyRaised': return `Asked the student to fix something: ${str(p.description)}`
      + (p.due_at ? ` (by ${new Date(str(p.due_at)).toLocaleDateString('en-IN')}).` : '.');
    case 'DeficiencyResponded': {
      const docs = Array.isArray(p.document_ids) ? p.document_ids.length : 0;
      return `The student replied: “${str(p.response_text)}”${docs ? ` with ${docs} document${docs > 1 ? 's' : ''}` : ''}.`;
    }
    case 'Resubmitted': return 'All requested fixes were answered; back with the institute.';
    case 'Sanctioned': {
      const n = Array.isArray(p.instalments) ? p.instalments.length : 0;
      const override = p.override ? ' Outside the rules, with a recorded reason.' : '';
      return `Sanctioned ${money(p.total_amount)} in ${n} instalment${n === 1 ? '' : 's'}.${override}`;
    }
    case 'Rejected': return `Rejected${p.note ? `: ${str(p.note)}` : '.'}`;
    case 'PaymentInitiated': return `Instalment ${str(p.instalment)} (${money(p.amount)}) sent to PFMS for transfer.`;
    case 'PaymentCredited': return `Instalment ${str(p.instalment)} (${money(p.amount)}) credited to the bank account.`;
    case 'PaymentFailed': return `Instalment ${str(p.instalment)} (${money(p.amount)}) failed: ${humanize(str(p.failure_code) || 'unknown reason')}.`;
    case 'ScholarshipSurrendered': return `Surrendered: ${str(p.reason)}.`;
    case 'OneSchemeRuleAcknowledged': return 'The student acknowledged they must give up their current scholarship if this one is sanctioned.';
    case 'ReviewCaseOpened': return `${humanize(str(p.claim_type))} needs an officer to check it.`;
    case 'ReviewDecisionRecorded':
      return `${humanize(str(p.claim_type))}: an officer chose ${humanize(str(p.decision)).toLowerCase()}.`;
    case 'SLABreached': return `Waited longer than the target in ${stateLabel(str(p.state))}; escalated.`;
    case 'RenewalDue': return 'Due for renewal for the next academic year.';
    default:
      if (p.from_state && p.to_state) return `Moved from ${stateLabel(str(p.from_state))} to ${stateLabel(str(p.to_state))}.`;
      return humanize(type.replace(/([a-z])([A-Z])/g, '$1_$2'));
  }
}
