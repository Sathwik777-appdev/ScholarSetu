// Shapes returned by the ScholarSetu Core API (/v1). Keep in step with services/core/app/*/schemas.py.

export type CanonicalState =
  | 'DRAFT' | 'SUBMITTED' | 'INSTITUTE_VERIFICATION' | 'DEFICIENCY_RAISED' | 'RESUBMITTED'
  | 'AUTHORITY_VERIFICATION' | 'SANCTIONED' | 'REJECTED' | 'PAYMENT_INITIATED' | 'CREDITED'
  | 'PAYMENT_FAILED' | 'RENEWAL_DUE' | 'SURRENDERED';

export type SchemeType = 'PRE_MATRIC' | 'POST_MATRIC' | 'TOP_CLASS' | 'NFST' | 'NOS';

export type UserRole =
  | 'STUDENT' | 'GUARDIAN' | 'MITRA' | 'INSTITUTE_OFFICER' | 'DISTRICT_OFFICER' | 'STATE_OFFICER' | 'MINISTRY';

export type ReviewDecision = 'APPROVE' | 'REJECT' | 'REQUEST_INFO';
export type ReviewCaseStatus = 'PENDING' | 'INFO_REQUESTED' | 'APPROVED' | 'REJECTED' | 'RESOLVED_BY_SOURCE';

export interface AuthUser {
  id: string;
  name: string;
  role: UserRole;
  student_id: string | null;
  household_id: string | null;
  jurisdiction_state: string | null;
  jurisdiction_district: string | null;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
}

export interface OfficerApplication {
  id: string;
  student_id: string;
  student_name: string;
  district: string;
  state_name: string;
  scheme: SchemeType;
  academic_year: string;
  source_system: string;
  source_ref: string | null;
  canonical_state: CanonicalState;
  state_changed_at: string;
  days_in_state: number;
  details: Record<string, unknown>;
  provisional_flags: string[];
  created_at: string;
}

export interface Application {
  id: string;
  student_id: string;
  scheme: SchemeType;
  academic_year: string;
  source_system: string;
  source_ref: string | null;
  canonical_state: CanonicalState;
  state_changed_at: string;
  details: Record<string, unknown>;
  provisional_flags: string[];
  created_at: string;
}

export interface LedgerEvent {
  event_id: string;
  position: number;
  application_id: string;
  sequence_no: number;
  type: string;
  source: string;
  actor: string;
  occurred_at: string;
  payload: Record<string, unknown>;
  hash_prev: string;
  hash: string;
}

export interface ChainVerification {
  application_id: string;
  valid: boolean;
  events_checked: number;
  first_invalid_event_id: string | null;
  reason: string | null;
}

export interface ReviewCase {
  id: string;
  student_id: string;
  student_name: string | null;
  application_id: string;
  claim_type: string;
  verification_status: string;
  reason: string;
  explanation: string;
  identity_score: number | null;
  evidence_refs: Record<string, unknown>[];
  attestation_id: string | null;
  status: ReviewCaseStatus;
  decision: ReviewDecision | null;
  decided_by: string | null;
  decided_at: string | null;
  notes: string | null;
  decision_event_id: string | null;
  sla_deadline: string;
}

export interface ReviewDecisionResponse {
  case: ReviewCase;
  ledger_event_id: string;
  attestation_id: string | null;
  attestation_status: string | null;
}

export interface AnalyticsOverview {
  scope: string;
  total_applications: number;
  total_students: number;
  by_state: { key: CanonicalState; count: number }[];
  by_scheme: { scheme: SchemeType; applications: number; sanctioned: string; credited: string }[];
  sanctioned_amount: string;
  credited_amount: string;
  failed_amount: string;
  pending_amount: string;
  payments_failed: number;
  payments_total: number;
  open_sla_breaches: number;
  open_review_cases: number;
}

export interface SLARow {
  application_id: string;
  scheme: SchemeType;
  state: CanonicalState;
  district: string;
  state_name: string;
  days_in_state: number;
  sla_days: number;
  breached: boolean;
}

export interface CoverageRow {
  district: string;
  block: string | null;
  enrolled_st: number;
  with_scholarship: number;
  coverage_pct: number;
  pvtg_enrolled: number;
  pvtg_with_scholarship: number;
  pvtg_coverage_pct: number | null;
}

export interface CoverageReport {
  level: string;
  method: string;
  matched_by_apaar: number;
  matched_by_clk: number;
  rows: CoverageRow[];
}

export interface BottleneckRow {
  district: string;
  state_name: string;
  stage: string;
  open_applications: number;
  avg_days_in_stage: number;
  sla_breaches: number;
}

export interface DBTHotspotRow {
  state_name: string;
  district: string;
  applications_checked: number;
  failing: number;
  failure_rate_pct: number;
  issue_counts: Record<string, number>;
}

export interface TransitionRow {
  state_name: string;
  district: string;
  from_scheme: string;
  to_scheme: string;
  previous_year: string;
  current_year: string;
  eligible_cohort: number;
  applied: number;
  conversion_pct: number | null;
}

export interface DBTStatus {
  application_id: string;
  latest_health_check: {
    id: string;
    overall_status: string;
    issues: { code: string; message?: string }[];
    bank_account_masked: string | null;
    checked_at: string;
  } | null;
  payments: {
    payment_id: string;
    instalment: number;
    amount: number;
    state: string;
    failure_code: string | null;
  }[];
  retries: { id: string; status: string }[];
}
