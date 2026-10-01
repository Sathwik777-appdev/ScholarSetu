"""Data requests (DPDP Act): a student's erasure or correction request and its decision.

Revision ID: 0009
Revises: 0008
"""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("student_id", sa.String(), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("requested_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("resolved_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_data_requests_student_id", "data_requests", ["student_id"])
    op.create_index("ix_data_requests_status", "data_requests", ["status"])


def downgrade() -> None:
    op.drop_index("ix_data_requests_status", table_name="data_requests")
    op.drop_index("ix_data_requests_student_id", table_name="data_requests")
    op.drop_table("data_requests")
