from fastapi import APIRouter, Depends

from app.dependencies import OFFICER_ROLES, Reader, StudentPrincipal, officer_or_student, require_role, student_principal
from app.gateway.models import User
from app.ledger.router import ensure_application_access
from app.ledger.service import LedgerService, get_ledger_service
from app.shared.types import MitraScope
from .schemas import DBTHealthCheckResult, DBTRetryResult, DBTStatus
from .service import DBTGuardianService

router = APIRouter(prefix="/v1", tags=["DBT Guardian"])


def get_dbt_service() -> DBTGuardianService:
    return DBTGuardianService()


@router.post("/dbt/health-check/{application_id}", response_model=DBTHealthCheckResult)
async def health_check(
    application_id: str,
    officer: User = Depends(require_role(*OFFICER_ROLES)),
    ledger: LedgerService = Depends(get_ledger_service),
    service: DBTGuardianService = Depends(get_dbt_service),
):
    """Run pre-sanction health checks (officers)."""
    ensure_application_access(ledger, application_id, Reader(user=officer, student_id=None))
    return await service.pre_sanction_check(application_id)


@router.get("/dbt/status/{application_id}", response_model=DBTStatus)
async def dbt_status(
    application_id: str,
    reader: Reader = Depends(officer_or_student(MitraScope.VIEW_STATUS)),
    ledger: LedgerService = Depends(get_ledger_service),
    service: DBTGuardianService = Depends(get_dbt_service),
):
    """Get full DBT status for an application (its owner or an officer)."""
    ensure_application_access(ledger, application_id, reader)
    return await service.get_dbt_status(application_id)


@router.post("/dbt/retry/{retry_id}/confirm", response_model=DBTRetryResult)
async def confirm_retry(
    retry_id: str,
    principal: StudentPrincipal = Depends(student_principal()),
    service: DBTGuardianService = Depends(get_dbt_service),
):
    """Student confirms a bank fix and asks for a retry."""
    # TODO(Phase 8): tie retry_id to the student's payment and run the DBT retry workflow.
    return await service.confirm_fix_and_retry(retry_id)
