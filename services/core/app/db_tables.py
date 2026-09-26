"""Tables backed by real models today.

Until the Phase 4 Alembic migration exists, scripts/seed_demo.py and the test suite create
exactly these tables. Legacy placeholder models elsewhere are deliberately not listed.
"""

from app.attestation.models import Attestation
from app.gateway.models import AssistSession, AuditLog, OtpChallenge, OutboundSms, User
from app.students.models import Student
from app.verification.models import ReviewCase

LIVE_TABLES = [
    User.__table__, OtpChallenge.__table__, AssistSession.__table__, AuditLog.__table__, OutboundSms.__table__,
    Student.__table__, Attestation.__table__, ReviewCase.__table__,
]
