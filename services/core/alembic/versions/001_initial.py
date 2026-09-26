"""Initial migration

Revision ID: 001_initial
Revises: 
Create Date: 2026-09-25 20:00:21.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # We create the enums first
    sa.Enum('STUDENT', 'GUARDIAN', 'MITRA', 'INSTITUTE_OFFICER', 'DISTRICT_OFFICER', 'STATE_OFFICER', 'MINISTRY', name='user_role_enum').create(op.get_bind())
    sa.Enum('MALE', 'FEMALE', 'OTHER', name='gender_enum').create(op.get_bind())
    sa.Enum('PRE_MATRIC', 'POST_MATRIC', 'HIGHER_EDUCATION', 'FELLOWSHIP', 'NATIONAL_OVERSEAS', name='scheme_type_enum').create(op.get_bind())
    sa.Enum('NSP', 'SFMP', 'NOS', 'SCHOLARSETU', 'DIGILOCKER', 'UIDAI', 'NPCI', name='source_system_enum').create(op.get_bind())
    sa.Enum('DRAFT', 'SUBMITTED', 'VERIFIED_INSTITUTE', 'VERIFIED_DISTRICT', 'VERIFIED_STATE', 'SANCTIONED', 'PAYMENT_INITIATED', 'DISBURSED', 'REJECTED', 'DEFICIENT', name='canonical_state_enum').create(op.get_bind())
    sa.Enum('INITIATED', 'PROCESSING', 'SUCCESS', 'FAILED', name='payment_state_enum').create(op.get_bind())
    sa.Enum('IDENTITY', 'CASTE', 'INCOME', 'ACADEMIC', 'BANK', name='claim_type_enum').create(op.get_bind())
    sa.Enum('API', 'MANUAL', 'DOCUMENT', 'AADHAAR_OTP', 'BIOMETRIC', name='verification_method_enum').create(op.get_bind())
    sa.Enum('APPROVED', 'REJECTED', 'NEED_MORE_INFO', name='review_decision_enum').create(op.get_bind())
    sa.Enum('ACTIVE', 'REVOKED', 'EXPIRED', name='attestation_status_enum').create(op.get_bind())
    sa.Enum('SMS', 'EMAIL', 'WHATSAPP', 'IN_APP', name='notification_channel_enum').create(op.get_bind())
    sa.Enum('APPLICATION_ENTRY', 'DOCUMENT_UPLOAD', 'STATUS_CHECK', name='mitra_scope_enum').create(op.get_bind())
    
    # pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('phone', sa.String(15), nullable=False, unique=True, index=True),
        sa.Column('aadhaar_ref_token', sa.String(), nullable=True),
        sa.Column('role', postgresql.ENUM(name='user_role_enum', create_type=False), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'households',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('guardian_name', sa.String(), nullable=False),
        sa.Column('guardian_phone', sa.String(15), nullable=False),
        sa.Column('guardian_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'students',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('apaar_id_hash', sa.String(), nullable=True, index=True),
        sa.Column('full_name', sa.String(), nullable=False),
        sa.Column('name_variants', postgresql.JSONB(), nullable=False),
        sa.Column('dob', sa.Date(), nullable=False),
        sa.Column('gender', postgresql.ENUM(name='gender_enum', create_type=False), nullable=False),
        sa.Column('tribe', sa.String(), nullable=False),
        sa.Column('pvtg_flag', sa.Boolean(), nullable=False),
        sa.Column('state', sa.String(), nullable=False),
        sa.Column('district', sa.String(), nullable=False),
        sa.Column('block', sa.String(), nullable=True),
        sa.Column('preferred_language', sa.String(10), nullable=False),
        sa.Column('household_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('households.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'mitra_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('mitra_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('students.id'), nullable=False),
        sa.Column('scope', postgresql.ENUM(name='mitra_scope_enum', create_type=False), nullable=False),
        sa.Column('otp_verified', sa.Boolean(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actions_log', postgresql.JSONB(), nullable=True),
    )

    op.create_table(
        'applications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('display_id', sa.String(), nullable=False, unique=True),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('students.id'), nullable=False, index=True),
        sa.Column('scheme', postgresql.ENUM(name='scheme_type_enum', create_type=False), nullable=False),
        sa.Column('source_system', postgresql.ENUM(name='source_system_enum', create_type=False), nullable=False),
        sa.Column('source_ref', sa.String(), nullable=True),
        sa.Column('academic_year', sa.String(), nullable=False),
        sa.Column('canonical_state', postgresql.ENUM(name='canonical_state_enum', create_type=False), nullable=False, index=True),
        sa.Column('provisional_flags', postgresql.JSONB(), nullable=True),
        sa.Column('applied_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_app_scheme_year', 'applications', ['scheme', 'academic_year'])

    op.create_table(
        'ledger_events',
        sa.Column('event_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('application_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('applications.id'), nullable=False),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('students.id'), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('scheme', postgresql.ENUM(name='scheme_type_enum', create_type=False), nullable=False),
        sa.Column('source', postgresql.ENUM(name='source_system_enum', create_type=False), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('payload', postgresql.JSONB(), nullable=False),
        sa.Column('hash_prev', sa.String(), nullable=False),
        sa.Column('hash', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_ledger_app_occurred', 'ledger_events', ['application_id', 'occurred_at'])

    op.create_table(
        'deficiencies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('application_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('applications.id'), nullable=False),
        sa.Column('code', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('raised_by_role', sa.String(), nullable=False),
        sa.Column('raised_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('response_payload', postgresql.JSONB(), nullable=True),
    )

    op.create_table(
        'payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('application_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('applications.id'), nullable=False, index=True),
        sa.Column('instalment', sa.Integer(), nullable=False),
        sa.Column('amount_sanctioned', sa.Numeric(12, 2), nullable=False),
        sa.Column('amount_credited', sa.Numeric(12, 2), nullable=True),
        sa.Column('state', postgresql.ENUM(name='payment_state_enum', create_type=False), nullable=False),
        sa.Column('failure_code', sa.String(), nullable=True),
        sa.Column('failure_message', sa.String(), nullable=True),
        sa.Column('pfms_ref', sa.String(), nullable=True),
        sa.Column('initiated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('credited_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'verification_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('application_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('applications.id'), nullable=True),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('students.id'), nullable=False),
        sa.Column('claim_type', postgresql.ENUM(name='claim_type_enum', create_type=False), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('source_used', sa.String(), nullable=False),
        sa.Column('method', postgresql.ENUM(name='verification_method_enum', create_type=False), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('result_payload', postgresql.JSONB(), nullable=True),
        sa.Column('evidence_hash', sa.String(), nullable=True),
        sa.Column('reasons', postgresql.JSONB(), nullable=True),
        sa.Column('requested_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'review_cases',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('application_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('applications.id'), nullable=False),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('students.id'), nullable=False),
        sa.Column('reason', sa.String(), nullable=False),
        sa.Column('claim_type', postgresql.ENUM(name='claim_type_enum', create_type=False), nullable=False),
        sa.Column('evidence_refs', postgresql.JSONB(), nullable=False),
        sa.Column('explanation', sa.String(), nullable=False),
        sa.Column('assigned_to', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('decision', postgresql.ENUM(name='review_decision_enum', create_type=False), nullable=True),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('decided_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('sla_deadline', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'attestations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('students.id'), nullable=False),
        sa.Column('claim_type', postgresql.ENUM(name='claim_type_enum', create_type=False), nullable=False),
        sa.Column('claim_value', postgresql.JSONB(), nullable=False),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('method', postgresql.ENUM(name='verification_method_enum', create_type=False), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('evidence_hash', sa.String(), nullable=False),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', postgresql.ENUM(name='attestation_status_enum', create_type=False), nullable=False),
        sa.Column('signature', sa.String(), nullable=False),
        sa.Column('verification_request_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('verification_requests.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_attest_student_claim_status', 'attestations', ['student_id', 'claim_type', 'status'])

    op.create_table(
        'rule_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('scheme', postgresql.ENUM(name='scheme_type_enum', create_type=False), nullable=False),
        sa.Column('version', sa.String(), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('effective_until', sa.Date(), nullable=True),
        sa.Column('decision_table', postgresql.JSONB(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'eligibility_checks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('students.id'), nullable=False),
        sa.Column('scheme', postgresql.ENUM(name='scheme_type_enum', create_type=False), nullable=False),
        sa.Column('rule_version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('rule_versions.id'), nullable=False),
        sa.Column('is_eligible', sa.Boolean(), nullable=False),
        sa.Column('reasons', postgresql.JSONB(), nullable=False),
        sa.Column('checked_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'dbt_health_checks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('application_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('applications.id'), nullable=False),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('students.id'), nullable=False),
        sa.Column('aadhaar_seeded', sa.Boolean(), nullable=True),
        sa.Column('account_active', sa.Boolean(), nullable=True),
        sa.Column('name_match_score', sa.Float(), nullable=True),
        sa.Column('account_type_ok', sa.Boolean(), nullable=True),
        sa.Column('overall_status', sa.String(), nullable=False),
        sa.Column('issues', postgresql.JSONB(), nullable=False),
        sa.Column('checked_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'dbt_retries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('payments.id'), nullable=False),
        sa.Column('attempt_number', sa.Integer(), nullable=False),
        sa.Column('failure_code', sa.String(), nullable=False),
        sa.Column('plain_message', sa.String(), nullable=False),
        sa.Column('fix_confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('retry_initiated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('result', sa.String(), nullable=True),
    )

    op.create_table(
        'wallet_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('students.id'), nullable=False),
        sa.Column('document_type', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('digilocker_uri', sa.String(), nullable=True),
        sa.Column('storage_key', sa.String(), nullable=True),
        sa.Column('content_hash', sa.String(), nullable=False),
        sa.Column('mime_type', sa.String(), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('metadata_json', postgresql.JSONB(), nullable=True),
    )

    op.create_table(
        'consents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('students.id'), nullable=False),
        sa.Column('requester', sa.String(), nullable=False),
        sa.Column('data_items', postgresql.JSONB(), nullable=False),
        sa.Column('purpose', sa.String(), nullable=False),
        sa.Column('granted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('artefact_signature', sa.String(), nullable=False),
    )

    op.create_table(
        'notification_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('channel', postgresql.ENUM(name='notification_channel_enum', create_type=False), nullable=False),
        sa.Column('language', sa.String(), nullable=False),
        sa.Column('subject', sa.String(), nullable=True),
        sa.Column('body_template', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'notification_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('students.id'), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('channel', postgresql.ENUM(name='notification_channel_enum', create_type=False), nullable=False),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('notification_templates.id'), nullable=True),
        sa.Column('rendered_body', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'conversation_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('students.id'), nullable=False),
        sa.Column('channel', sa.String(), nullable=False),
        sa.Column('messages', postgresql.JSONB(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'guideline_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('scheme', postgresql.ENUM(name='scheme_type_enum', create_type=False), nullable=True),
        sa.Column('section', sa.String(), nullable=False),
        sa.Column('content', sa.String(), nullable=False),
        sa.Column('embedding', sa.String(), nullable=False), # using simple string/json fallback or pgvector Vector type representation
        sa.Column('source_document', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    # Re-declare embedding properly if vector is installed:
    op.execute("ALTER TABLE guideline_chunks ALTER COLUMN embedding TYPE vector(384) USING embedding::vector")


    op.create_table(
        'coverage_analyses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('analysis_date', sa.Date(), nullable=False),
        sa.Column('state', sa.String(), nullable=False),
        sa.Column('district', sa.String(), nullable=False),
        sa.Column('block', sa.String(), nullable=True),
        sa.Column('total_enrolled_st', sa.Integer(), nullable=False),
        sa.Column('total_scholarship_holders', sa.Integer(), nullable=False),
        sa.Column('coverage_pct', sa.Float(), nullable=False),
        sa.Column('scheme_breakdown', postgresql.JSONB(), nullable=False),
        sa.Column('pvtg_coverage_pct', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'outreach_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('analysis_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('coverage_analyses.id'), nullable=False),
        sa.Column('institution_code', sa.String(), nullable=False),
        sa.Column('institution_name', sa.String(), nullable=False),
        sa.Column('unreached_count', sa.Integer(), nullable=False),
        sa.Column('sent_to', sa.String(), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
    )


def downgrade() -> None:
    pass
