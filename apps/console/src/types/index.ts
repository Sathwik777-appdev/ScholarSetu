export enum CanonicalState {
  DRAFT = 'DRAFT',
  SUBMITTED = 'SUBMITTED',
  INSTITUTE_VERIFICATION = 'INSTITUTE_VERIFICATION',
  DEFICIENCY_RAISED = 'DEFICIENCY_RAISED',
  RESUBMITTED = 'RESUBMITTED',
  AUTHORITY_VERIFICATION = 'AUTHORITY_VERIFICATION',
  SANCTIONED = 'SANCTIONED',
  REJECTED = 'REJECTED',
  PAYMENT_INITIATED = 'PAYMENT_INITIATED',
  CREDITED = 'CREDITED',
  PAYMENT_FAILED = 'PAYMENT_FAILED',
  RENEWAL_DUE = 'RENEWAL_DUE',
}

export enum SchemeType {
  PRE_MATRIC = 'PRE_MATRIC',
  POST_MATRIC = 'POST_MATRIC',
  TOP_CLASS = 'TOP_CLASS',
  NFST = 'NFST',
  NOS = 'NOS',
}

export interface Application {
  id: string;
  display_id: string;
  student_name: string;
  scheme: SchemeType;
  academic_year: string;
  canonical_state: CanonicalState;
  applied_at: string;
  district: string;
  institution: string;
  days_in_current_state: number;
  provisional_flags: string[];
}

export interface TimelineEvent {
  event_id: string;
  event_type: string;
  occurred_at: string;
  actor: string;
  description: string;
  details: Record<string, any>;
}

export interface ReviewCase {
  id: string;
  application_id: string;
  student_name: string;
  reason: string;
  claim_type: string;
  explanation: string;
  evidence_refs: string[];
  sla_deadline: string;
  days_remaining: number;
  created_at: string;
}

export interface CoverageData {
  state: string;
  district: string;
  total_enrolled: number;
  total_scholarship: number;
  coverage_pct: number;
  pvtg_coverage_pct: number;
}

export interface BottleneckEntry {
  state: string;
  district: string;
  stage: CanonicalState;
  avg_days_stuck: number;
  count: number;
}

export interface DBTFailure {
  district: string;
  failure_count: number;
  failure_rate: number;
  common_codes: string[];
}

export interface AnalyticsOverview {
  total_applications: number;
  total_students: number;
  total_sanctioned_amount: number;
  total_credited_amount: number;
  by_scheme: { scheme: SchemeType; count: number; sanctioned: number; credited: number }[];
  by_state: { state: CanonicalState; count: number }[];
  avg_processing_days: number;
  sla_breach_count: number;
}

export interface PaymentSummary {
  total_sanctioned: number;
  total_credited: number;
  total_failed: number;
  total_pending: number;
  failure_rate: number;
}
