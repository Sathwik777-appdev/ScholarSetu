from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import Reader, StudentPrincipal, officer_or_student, student_principal
from app.ledger.router import actor_of, ensure_application_access
from app.shared.types import MitraScope
from .schemas import DBTHealthCheckResult, DBTRetryOut, DBTStatus, RetryRequest
from .service import DBTError, DBTGuardianService, get_dbt_service, health_result

router = APIRouter(prefix="/v1", tags=["DBT Guardian"])


def _http(exc: DBTError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.post("/dbt/health-check/{application_id}", response_model=DBTHealthCheckResult)
async def health_check(application_id: str, reader: Reader = Depends(officer_or_student(MitraScope.VIEW_STATUS)),
                       service: DBTGuardianService = Depends(get_dbt_service)):
    """Pre-sanction check: Aadhaar seeding, account status, account-holder name and account type."""
    app = await ensure_application_access(service.ledger, application_id, reader)
    try:
        check = await service.health_check(app, actor_of(reader.user))
    except DBTError as exc:
        raise _http(exc)
    await service.db.commit()
    return health_result(check)


@router.get("/dbt/status/{application_id}", response_model=DBTStatus)
async def dbt_status(application_id: str, reader: Reader = Depends(officer_or_student(MitraScope.VIEW_STATUS)),
                     service: DBTGuardianService = Depends(get_dbt_service)):
    app = await ensure_application_access(service.ledger, application_id, reader)
    return await service.status(app)


@router.post("/dbt/applications/{application_id}/payments/{payment_id}/retry", response_model=DBTRetryOut)
async def retry_payment(application_id: str, payment_id: str, body: RetryRequest,
                        principal: StudentPrincipal = Depends(student_principal()),
                        service: DBTGuardianService = Depends(get_dbt_service)):
    """After fixing the bank problem, the student asks for the failed payment to be sent again."""
    if not body.confirm_fixed:
        raise HTTPException(status_code=422, detail="Confirm that the bank problem has been fixed")
    app = await ensure_application_access(service.ledger, application_id, Reader(principal.user, principal.student_id))
    try:
        retry = await service.request_retry(app, payment_id, actor_of(principal.user))
    except DBTError as exc:
        raise _http(exc)
    await service.db.commit()
    return retry


@router.post("/dbt/applications/{application_id}/simulate-bank-fix", status_code=204)
async def simulate_bank_fix(application_id: str,
                            principal: StudentPrincipal = Depends(student_principal()),
                            service: DBTGuardianService = Depends(get_dbt_service)):
    """Demo only (404 otherwise): pretend the bank fixed the student's account in the test bank service."""
    app = await ensure_application_access(service.ledger, application_id, Reader(principal.user, principal.student_id))
    try:
        await service.simulate_bank_fix(app, actor_of(principal.user))
    except DBTError as exc:
        raise _http(exc)
