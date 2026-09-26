import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any
from app.wallet.schemas import WalletDocumentResponse, WalletResponse


class WalletService:
    """Manages student digital document wallet with DigiLocker sync."""

    def __init__(self, db=None):
        self.db = db
        self._wallet_docs: Dict[str, List[WalletDocumentResponse]] = {}
        self._seed_demo_wallet()

    def _seed_demo_wallet(self):
        student_id = "stu-sunita-001"
        now = datetime.now(timezone.utc).isoformat()
        self._wallet_docs[student_id] = [
            WalletDocumentResponse(
                id="doc_dl_caste_001",
                student_id=student_id,
                document_type="CASTE_CERTIFICATE",
                title="Scheduled Tribe Certificate (Santal)",
                source="DIGILOCKER",
                digilocker_uri="in.gov.jharkhand.edistrict:caste:JH-ST-2022-8821",
                content_hash="sha256:4a8b9c0d1e2f3a4b5c6d7e8f",
                mime_type="application/pdf",
                size_bytes=245100,
                uploaded_at=now,
                verified=True,
                metadata_json={"issuing_authority": "Circle Officer, Dumka", "tribe": "Santal"}
            ),
            WalletDocumentResponse(
                id="doc_dl_marksheet10_001",
                student_id=student_id,
                document_type="MARKSHEET_10",
                title="Class 10 Matriculation Marksheet (JAC)",
                source="DIGILOCKER",
                digilocker_uri="in.gov.jac:marksheet:2026-X-109283",
                content_hash="sha256:7b8c9d0e1f2a3b4c5d6e7f8a",
                mime_type="application/pdf",
                size_bytes=312400,
                uploaded_at=now,
                verified=True,
                metadata_json={"board": "Jharkhand Academic Council", "year": "2026", "percentage": 84.5}
            ),
            WalletDocumentResponse(
                id="doc_dl_aadhaar_001",
                student_id=student_id,
                document_type="AADHAAR",
                title="Aadhaar Card (e-Aadhaar)",
                source="DIGILOCKER",
                digilocker_uri="in.gov.uidai:aadhaar:XXXX-XXXX-4912",
                content_hash="sha256:9f8e7d6c5b4a3a2b1c0d9e8f",
                mime_type="application/pdf",
                size_bytes=184200,
                uploaded_at=now,
                verified=True,
                metadata_json={"name": "Sunita Hansda", "dob": "2008-04-12"}
            )
        ]

    async def get_wallet(self, student_id: str) -> WalletResponse:
        docs = self._wallet_docs.get(student_id, [])
        return WalletResponse(
            student_id=student_id,
            total_documents=len(docs),
            documents=docs
        )

    async def pull_from_digilocker(self, student_id: str, doc_type: str) -> WalletDocumentResponse:
        now = datetime.now(timezone.utc).isoformat()
        new_doc = WalletDocumentResponse(
            id=f"doc_dl_{uuid.uuid4().hex[:8]}",
            student_id=student_id,
            document_type=doc_type,
            title=f"DigiLocker Verified {doc_type.replace('_', ' ').title()}",
            source="DIGILOCKER",
            digilocker_uri=f"in.gov.digilocker:{doc_type.lower()}:{uuid.uuid4().hex[:10]}",
            content_hash=f"sha256:{uuid.uuid4().hex}",
            mime_type="application/pdf",
            size_bytes=215000,
            uploaded_at=now,
            verified=True,
            metadata_json={"source": "DigiLocker National Gateway", "synced_at": now}
        )
        if student_id not in self._wallet_docs:
            self._wallet_docs[student_id] = []
        self._wallet_docs[student_id].append(new_doc)
        return new_doc


global_wallet_service = WalletService()


def get_wallet_service() -> WalletService:
    return global_wallet_service
