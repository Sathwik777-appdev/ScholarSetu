from pydantic import BaseModel
from typing import Optional, Dict, Any, List


class WalletDocumentResponse(BaseModel):
    id: str
    student_id: str
    document_type: str
    title: str
    source: str                   # DIGILOCKER | DIGILOCKER_TEST | UPLOAD
    source_label: str = ""        # how to show it: "DigiLocker", "DigiLocker (test)", "Uploaded by you"
    test_document: bool = False   # true for documents from a mock or sandbox DigiLocker (test data)
    digilocker_uri: Optional[str] = None
    content_hash: str
    mime_type: str
    size_bytes: int
    uploaded_at: str
    verified: bool = False  # true only when the issuer signed it (the real DigiLocker); never for test documents
    metadata_json: Optional[Dict[str, Any]] = None


class WalletResponse(BaseModel):
    student_id: str
    total_documents: int
    documents: List[WalletDocumentResponse]
