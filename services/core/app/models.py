"""Import every model so Base.metadata (Alembic, tests) sees the whole schema."""

from app.adapters.models import ParkedEvent  # noqa: F401
from app.attestation.models import Attestation  # noqa: F401
from app.jago_skill.models import GuidelineChunk  # noqa: F401
from app.consent.models import Consent  # noqa: F401
from app.dbt_guardian.models import DbtHealthCheck, DbtRetry  # noqa: F401
from app.eligibility.models import EligibilityDecision, RuleVersion  # noqa: F401
from app.gateway.models import AssistSession, AuditLog, OtpChallenge, OutboundSms, User  # noqa: F401
from app.ledger.models import Application, Deficiency, Household, LedgerEvent, OutboxMessage, Payment  # noqa: F401
from app.nudge.models import Notification  # noqa: F401
from app.students.models import Student  # noqa: F401
from app.verification.models import ReviewCase  # noqa: F401
from app.wallet.models import WalletDocument  # noqa: F401
from app.sync.models import SyncReceipt  # noqa: F401
