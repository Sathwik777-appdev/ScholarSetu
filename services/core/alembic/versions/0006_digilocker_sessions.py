"""DigiLocker partner sign-in sessions (OAuth state, PKCE verifier, short-lived token).

Revision ID: 0006
Revises: 0005
"""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "digilocker_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("student_id", sa.String(), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("state", sa.String(64), nullable=False, unique=True),
        sa.Column("code_verifier", sa.String(128), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("access_token", sa.String(512), nullable=True),
        sa.Column("digilocker_name", sa.String(), nullable=True),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_digilocker_sessions_student_id", "digilocker_sessions", ["student_id"])


def downgrade() -> None:
    op.drop_index("ix_digilocker_sessions_student_id", table_name="digilocker_sessions")
    op.drop_table("digilocker_sessions")
