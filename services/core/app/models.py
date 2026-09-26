"""Import every model so Base.metadata (Alembic, tests) sees the whole schema."""

from app.attestation.models import Attestation  # noqa: F401
from app.gateway.models import AssistSession, AuditLog, OtpChallenge, OutboundSms, User  # noqa: F401
from app.ledger.models import Application, Deficiency, Household, LedgerEvent, OutboxMessage, Payment  # noqa: F401
from app.nudge.models import Notification  # noqa: F401
from app.students.models import Student  # noqa: F401
from app.verification.models import ReviewCase  # noqa: F401
from app.wallet.models import WalletDocument  # noqa: F401
