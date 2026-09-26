import { CanonicalState } from '../types';

export const STATUS_COLORS: Record<CanonicalState, string> = {
  [CanonicalState.DRAFT]: 'bg-gray-100 text-gray-800',
  [CanonicalState.SUBMITTED]: 'bg-blue-100 text-blue-800',
  [CanonicalState.INSTITUTE_VERIFICATION]: 'bg-yellow-100 text-yellow-800',
  [CanonicalState.DEFICIENCY_RAISED]: 'bg-red-100 text-red-800',
  [CanonicalState.RESUBMITTED]: 'bg-orange-100 text-orange-800',
  [CanonicalState.AUTHORITY_VERIFICATION]: 'bg-purple-100 text-purple-800',
  [CanonicalState.SANCTIONED]: 'bg-indigo-100 text-indigo-800',
  [CanonicalState.REJECTED]: 'bg-red-200 text-red-900',
  [CanonicalState.PAYMENT_INITIATED]: 'bg-teal-100 text-teal-800',
  [CanonicalState.CREDITED]: 'bg-green-100 text-green-800',
  [CanonicalState.PAYMENT_FAILED]: 'bg-rose-100 text-rose-800',
  [CanonicalState.RENEWAL_DUE]: 'bg-pink-100 text-pink-800',
};

export const STATUS_LABELS: Record<CanonicalState, string> = {
  [CanonicalState.DRAFT]: 'Draft',
  [CanonicalState.SUBMITTED]: 'Submitted',
  [CanonicalState.INSTITUTE_VERIFICATION]: 'Institute Verification',
  [CanonicalState.DEFICIENCY_RAISED]: 'Deficiency Raised',
  [CanonicalState.RESUBMITTED]: 'Resubmitted',
  [CanonicalState.AUTHORITY_VERIFICATION]: 'Authority Verification',
  [CanonicalState.SANCTIONED]: 'Sanctioned',
  [CanonicalState.REJECTED]: 'Rejected',
  [CanonicalState.PAYMENT_INITIATED]: 'Payment Initiated',
  [CanonicalState.CREDITED]: 'Credited',
  [CanonicalState.PAYMENT_FAILED]: 'Payment Failed',
  [CanonicalState.RENEWAL_DUE]: 'Renewal Due',
};
