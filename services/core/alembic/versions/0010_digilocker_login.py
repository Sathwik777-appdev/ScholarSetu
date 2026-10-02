"""Sign in with DigiLocker: users.digilocker_id and the login attempts table.

Revision ID: 0010
Revises: fc89618e1774
"""

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "fc89618e1774"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("digilocker_id", sa.String(80), nullable=True))
    op.create_unique_constraint("uq_users_digilocker_id", "users", ["digilocker_id"])
    op.create_table(
        "digilocker_logins",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("state", sa.String(64), nullable=False, unique=True),
        sa.Column("code_verifier", sa.String(128), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("digilocker_id", sa.String(80), nullable=True),
        sa.Column("profile", sa.JSON(), nullable=True),
        sa.Column("registration_token", sa.String(64), nullable=True, unique=True),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("digilocker_logins")
    op.drop_constraint("uq_users_digilocker_id", "users", type_="unique")
    op.drop_column("users", "digilocker_id")
