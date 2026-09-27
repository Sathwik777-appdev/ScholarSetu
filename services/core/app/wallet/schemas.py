from pydantic import BaseModel
from typing import Optional, Dict, Any, List


class WalletDocumentResponse(BaseModel):
    id: str
    student_id: str
    document_type: str
    title: str
    source: str
    digilocker_uri: Optional[str] = None
    content_hash: str
    mime_type: str
    size_bytes: int
    uploaded_at: str
    verified: bool = False  # true only when the issuer signed the document (e.g. DigiLocker)
    metadata_json: Optional[Dict[str, Any]] = None


class WalletResponse(BaseModel):
    student_id: str
    total_documents: int
    documents: List[WalletDocumentResponse]
