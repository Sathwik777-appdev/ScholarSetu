"""One open application per student, scheme and academic year (enforced by the database).

Revision ID: 0007
Revises: 0006
"""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

# SURRENDERED was added to the enum in 0005; env.py commits each migration separately, so it is usable here.
OPEN = "canonical_state NOT IN ('REJECTED', 'SURRENDERED')"


def upgrade() -> None:
    duplicates = op.get_bind().execute(sa.text(
        f"SELECT student_id, scheme, academic_year, count(*) FROM applications WHERE {OPEN} "
        "GROUP BY 1, 2, 3 HAVING count(*) > 1")).fetchall()
    if duplicates:
        raise RuntimeError("Open duplicate applications must be resolved before this migration: "
                           + "; ".join(f"{d[0]} {d[1]} {d[2]} x{d[3]}" for d in duplicates))
    op.create_index("uq_application_open_per_scheme_year", "applications",
                    ["student_id", "scheme", "academic_year"], unique=True, postgresql_where=sa.text(OPEN))


def downgrade() -> None:
    op.drop_index("uq_application_open_per_scheme_year", table_name="applications")
