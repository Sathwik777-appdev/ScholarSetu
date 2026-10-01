"""Indexes on the normalised state and district keys that officer jurisdiction filters use.

Revision ID: 0008
Revises: 0007
"""

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

STATE = r"lower(regexp_replace(trim(state), '\s+', ' ', 'g'))"
DISTRICT = r"lower(regexp_replace(trim(district), '\s+', ' ', 'g'))"


def upgrade() -> None:
    op.execute(f"CREATE INDEX IF NOT EXISTS ix_students_state_key ON students ({STATE})")
    op.execute(f"CREATE INDEX IF NOT EXISTS ix_students_state_district_key ON students ({STATE}, {DISTRICT})")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_students_state_district_key")
    op.execute("DROP INDEX IF EXISTS ix_students_state_key")
