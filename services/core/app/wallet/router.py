from fastapi import APIRouter, Depends

from app.dependencies import StudentPrincipal, student_principal
from app.shared.types import MitraScope
from app.wallet.schemas import DigiLockerPullRequest, WalletDocumentResponse, WalletResponse
from app.wallet.service import WalletService, get_wallet_service

router = APIRouter(prefix="/v1", tags=["Document Wallet (DigiLocker)"])


@router.get("/me/wallet", response_model=WalletResponse)
async def get_my_wallet(
    principal: StudentPrincipal = Depends(student_principal(MitraScope.VIEW_STATUS, MitraScope.UPLOAD_DOCUMENTS)),
    service: WalletService = Depends(get_wallet_service),
):
    """Retrieve all documents in the student's digital wallet."""
    return await service.get_wallet(principal.student_id)


@router.post("/me/wallet/digilocker/pull", response_model=WalletDocumentResponse)
async def pull_from_digilocker(
    req: DigiLockerPullRequest,
    principal: StudentPrincipal = Depends(student_principal(MitraScope.UPLOAD_DOCUMENTS)),
    service: WalletService = Depends(get_wallet_service),
):
    """Pull a certificate/marksheet from DigiLocker into the wallet. TODO(Phase 7): real pull into MinIO."""
    from fastapi import HTTPException
    raise HTTPException(status_code=501, detail="DigiLocker pull is not implemented yet")
