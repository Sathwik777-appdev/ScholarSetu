"""SURRENDERED application state, CANCELLED payment state, OTP rate-limit index

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-28 12:00:00

"""
from typing import Sequence, Union

from alembic import op


revision: str = '0005'
down_revision: Union[str, None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE canonical_state ADD VALUE IF NOT EXISTS 'SURRENDERED'")
    op.execute("ALTER TYPE payment_state ADD VALUE IF NOT EXISTS 'CANCELLED'")
    op.create_index('ix_otp_challenges_phone_purpose_created', 'otp_challenges', ['phone', 'purpose', 'created_at'])


def downgrade() -> None:
    op.drop_index('ix_otp_challenges_phone_purpose_created', table_name='otp_challenges')
    # Postgres cannot drop enum values; SURRENDERED and CANCELLED stay in their types.
