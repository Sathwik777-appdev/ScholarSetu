"""DigiLocker import (ARCHITECTURE.md §6.1, §6.9): the authorised-partner OAuth 2.0 flow with PKCE.

1. The student taps "Get from DigiLocker": start() creates a session and returns DigiLocker's sign-in URL.
2. The student signs in to DigiLocker and allows access; DigiLocker redirects to our callback, which
   exchanges the code (with the PKCE verifier) for an access token: complete().
3. The app lists the student's issued documents (list_documents) and imports the chosen ones
   (import_documents); the token is then discarded.

The same client talks to the test DigiLocker (mocks/digilocker) and to the real service: only
settings change (DIGILOCKER_MODE, DIGILOCKER_API_URL, DIGILOCKER_AUTHORIZE_URL, client credentials).
Documents from a test DigiLocker are stored as DIGILOCKER_TEST and never marked issuer-signed.
"""

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import quote, urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.consent.service import ConsentService
from app.digilocker.models import DigiLockerSession
from app.gateway.models import User
from app.gateway.service import record_audit
from app.wallet.models import WalletDocument
from app.wallet.service import WalletService, digilocker_source, sniff_mime

SESSION_MINUTES = 15
TOKEN_PATH = "/public/oauth2/1/token"
ISSUED_PATH = "/public/oauth2/2/files/issued"
FILE_PATH = "/public/oauth2/1/file/"


class DigiLockerError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code, self.detail = status_code, detail


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def pkce_pair() -> tuple[str, str]:
    """(code_verifier, S256 code_challenge) as in RFC 7636."""
    verifier = secrets.token_urlsafe(64)[:96]
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


class DigiLockerService:
    def __init__(self, db: AsyncSession, http: httpx.AsyncClient):
        self.db = db
        self.http = http

    @staticmethod
    def _require_configured() -> None:
        if settings.DIGILOCKER_MODE == "mock":
            return
        if not (settings.DIGILOCKER_CLIENT_ID and settings.DIGILOCKER_CLIENT_SECRET):
            raise DigiLockerError(503, "DigiLocker is not configured on this server")

    async def start(self, student_id: str, user: User) -> tuple[DigiLockerSession, str]:
        self._require_configured()
        verifier, challenge = pkce_pair()
        session = DigiLockerSession(student_id=student_id, user_id=user.id, state=secrets.token_urlsafe(32),
                                    code_verifier=verifier, expires_at=_now() + timedelta(minutes=SESSION_MINUTES))
        self.db.add(session)
        await self.db.flush()
        client_id = settings.DIGILOCKER_CLIENT_ID or "scholarsetu-demo"
        url = settings.digilocker_authorize_url + "?" + urlencode({
            "response_type": "code", "client_id": client_id,
            "redirect_uri": settings.digilocker_redirect_uri, "state": session.state,
            "code_challenge": challenge, "code_challenge_method": "S256"})
        await record_audit(self.db, "DIGILOCKER_CONNECT_STARTED", actor=user, student_id=student_id,
                           details={"session_id": session.id, "mode": settings.DIGILOCKER_MODE})
        return session, url

    async def complete(self, state: str, code: Optional[str], error: Optional[str]) -> DigiLockerSession:
        """The OAuth callback: exchange the code for a token. Unknown or expired state is refused."""
        session = (await self.db.execute(
            select(DigiLockerSession).where(DigiLockerSession.state == state).with_for_update())).scalar_one_or_none()
        if session is None or session.status != "PENDING" or _aware(session.expires_at) < _now():
            raise DigiLockerError(400, "This DigiLocker sign-in link has expired or was already used")
        if error or not code:
            session.status, session.error = "FAILED", f"DigiLocker: {error or 'no code returned'}"
            return session
        client_id = settings.DIGILOCKER_CLIENT_ID or "scholarsetu-demo"
        client_secret = settings.DIGILOCKER_CLIENT_SECRET or "demo-secret-1234567890"
        try:
            res = await self.http.post(TOKEN_PATH, data={
                "grant_type": "authorization_code", "code": code, "client_id": client_id,
                "client_secret": client_secret, "redirect_uri": settings.digilocker_redirect_uri,
                "code_verifier": session.code_verifier})
        except httpx.TransportError:
            session.status, session.error = "FAILED", "DigiLocker could not be reached"
            return session
        if res.status_code != 200:
            session.status, session.error = "FAILED", f"DigiLocker refused the sign-in (HTTP {res.status_code})"
            return session
        body = res.json()
        session.access_token, session.digilocker_name = body.get("access_token"), body.get("name")
        session.status = "CONNECTED"
        return session

    async def get_session(self, session_id: str, student_id: str) -> DigiLockerSession:
        session = await self.db.get(DigiLockerSession, session_id)
        if session is None or session.student_id != student_id:
            raise DigiLockerError(404, "DigiLocker session not found")
        return session

    def _bearer(self, session: DigiLockerSession) -> dict:
        if session.status != "CONNECTED" or not session.access_token:
            raise DigiLockerError(409, f"The DigiLocker session is {session.status.lower()}")
        if _aware(session.expires_at) < _now():
            raise DigiLockerError(410, "The DigiLocker session expired; connect again")
        return {"Authorization": f"Bearer {session.access_token}"}

    async def list_documents(self, session: DigiLockerSession) -> list[dict]:
        headers = self._bearer(session)
        try:
            res = await self.http.get(ISSUED_PATH, headers=headers)
        except httpx.TransportError:
            raise DigiLockerError(503, "DigiLocker could not be reached; try again")
        if res.status_code == 401:
            session.status, session.access_token, session.error = "FAILED", None, "DigiLocker sign-in expired"
            raise DigiLockerError(410, "The DigiLocker sign-in expired; connect again")
        if res.status_code != 200:
            raise DigiLockerError(502, f"DigiLocker returned HTTP {res.status_code}")
        imported = set((await self.db.execute(select(WalletDocument.source_ref).where(
            WalletDocument.student_id == session.student_id))).scalars())
        return [{"uri": i["uri"], "doctype": i.get("doctype"), "name": i.get("name") or i.get("description"),
                 "issuer": i.get("issuer"), "already_imported": i["uri"] in imported}
                for i in res.json().get("items", []) if i.get("type", "file") == "file"]

    async def import_documents(self, session: DigiLockerSession, uris: list[str], user: User,
                               wallet: WalletService) -> list[WalletDocument]:
        available = {d["uri"]: d for d in await self.list_documents(session)}
        unknown = [u for u in uris if u not in available]
        if unknown:
            raise DigiLockerError(422, f"Not among the student's issued documents: {', '.join(unknown)}")
        chosen = [available[u] for u in dict.fromkeys(uris)]
        # The student chose these documents in the app: record that as a wallet consent for them.
        consent = await ConsentService(self.db).grant(
            session.student_id, "SCHOLARSETU_WALLET", "Import documents from DigiLocker into the wallet",
            [f"DIGILOCKER:{d['doctype']}" for d in chosen], 1, user)
        source, signed = digilocker_source()
        docs = []
        for d in chosen:
            existing = (await self.db.execute(select(WalletDocument).where(
                WalletDocument.student_id == session.student_id, WalletDocument.source_ref == d["uri"]))
            ).scalar_one_or_none()
            if existing is not None:
                docs.append(existing)
                continue
            try:
                res = await self.http.get(FILE_PATH + quote(d["uri"], safe=""), headers=self._bearer(session))
            except httpx.TransportError:
                raise DigiLockerError(503, "DigiLocker could not be reached; try again")
            if res.status_code != 200:
                raise DigiLockerError(502, f"DigiLocker did not return {d['name']} (HTTP {res.status_code})")
            mime = sniff_mime(res.content)
            if mime is None:
                raise DigiLockerError(502, f"DigiLocker returned {d['name']} in an unsupported format")
            title = f"{d['name']} ({d['issuer']})" + (" [test]" if settings.digilocker_is_test else "")
            doc = await wallet._store(session.student_id, res.content, mime, document_type=d["doctype"] or "OTHER",
                                      title=title[:200], source=source, source_ref=d["uri"], issuer=d["issuer"],
                                      issuer_signed=signed, uploaded_by=user.id,
                                      metadata_json={"consent_id": consent.id, "digilocker_session": session.id,
                                                     "digilocker_mode": settings.DIGILOCKER_MODE})
            await record_audit(self.db, "WALLET_DIGILOCKER_IMPORT", actor=user, student_id=session.student_id,
                               details={"document_id": doc.id, "doctype": d["doctype"], "consent_id": consent.id,
                                        "mode": settings.DIGILOCKER_MODE})
            docs.append(doc)
        session.status, session.access_token = "DONE", None  # the token is not kept after the import
        return docs
