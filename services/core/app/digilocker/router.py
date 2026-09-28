import html
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import StudentPrincipal, student_principal
from app.digilocker.service import DigiLockerError, DigiLockerService
from app.shared.types import MitraScope
from app.wallet.schemas import WalletDocumentResponse
from app.wallet.service import WalletService, to_response
from app.wallet.storage import StorageUnavailable, get_object_store

router = APIRouter(prefix="/v1", tags=["DigiLocker"])


async def get_digilocker_http():
    """FastAPI dependency: the server-to-server client for DigiLocker. Tests override its transport."""
    client = httpx.AsyncClient(base_url=settings.digilocker_api_url, timeout=10.0)
    try:
        yield client
    finally:
        await client.aclose()


async def get_digilocker_service(db: AsyncSession = Depends(get_db),
                                 http: httpx.AsyncClient = Depends(get_digilocker_http)) -> DigiLockerService:
    return DigiLockerService(db, http)


def _http(exc: DigiLockerError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


def _mode() -> dict:
    return {"mode": settings.DIGILOCKER_MODE, "test_service": settings.digilocker_is_test,
            "label": "DigiLocker (test)" if settings.digilocker_is_test else "DigiLocker"}


class ConnectResponse(BaseModel):
    session_id: str
    authorize_url: str
    mode: str
    test_service: bool
    label: str


class IssuedDocument(BaseModel):
    uri: str
    doctype: Optional[str] = None
    name: Optional[str] = None
    issuer: Optional[str] = None
    already_imported: bool = False


class SessionResponse(BaseModel):
    session_id: str
    status: str               # PENDING | CONNECTED | FAILED | DONE
    error: Optional[str] = None
    digilocker_name: Optional[str] = None
    documents: list[IssuedDocument] = []
    mode: str
    test_service: bool
    label: str


class ImportRequest(BaseModel):
    model_config = {"extra": "forbid"}
    uris: list[str] = Field(..., min_length=1, max_length=20)


class ImportResponse(BaseModel):
    imported: list[WalletDocumentResponse]


@router.post("/me/digilocker/connect", response_model=ConnectResponse, status_code=201)
async def connect(principal: StudentPrincipal = Depends(student_principal(MitraScope.UPLOAD_DOCUMENTS)),
                  service: DigiLockerService = Depends(get_digilocker_service)):
    """Start "Get from DigiLocker": returns the sign-in page to open in the browser."""
    try:
        session, url = await service.start(principal.student_id, principal.user)
    except DigiLockerError as exc:
        raise _http(exc)
    await service.db.commit()
    return ConnectResponse(session_id=session.id, authorize_url=url, **_mode())


def _result_page(title: str, message: str, ok: bool) -> HTMLResponse:
    colour = "#15803d" if ok else "#b91c1c"
    banner = ('<div style="background:#b45309;color:#fff;padding:10px 16px;font-weight:600;font-size:14px">'
              "DigiLocker (test): documents from this service are test data.</div>") if settings.digilocker_is_test else ""
    return HTMLResponse(status_code=200 if ok else 400, content=f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>ScholarSetu</title></head>
<body style="font-family:system-ui,sans-serif;margin:0;background:#f4f6fb;color:#0f172a">{banner}
<main style="max-width:420px;margin:24px auto;background:#fff;border-radius:16px;padding:24px">
<h2 style="margin-top:0;color:{colour}">{html.escape(title)}</h2><p>{html.escape(message)}</p></main></body></html>""")


@router.get("/digilocker/callback", response_class=HTMLResponse)
async def callback(state: str = "", code: Optional[str] = None, error: Optional[str] = None,
                   service: DigiLockerService = Depends(get_digilocker_service)):
    """DigiLocker redirects the student's browser here after sign-in. The code is exchanged server-side."""
    if not state:
        return _result_page("Sign-in not completed", "The link is incomplete. Go back to ScholarSetu and try again.",
                            False)
    try:
        session = await service.complete(state, code, error)
    except DigiLockerError as exc:
        return _result_page("Sign-in not completed", exc.detail, False)
    await service.db.commit()
    if session.status != "CONNECTED":
        return _result_page("Sign-in not completed", f"{session.error}. Go back to ScholarSetu and try again.", False)
    return _result_page("DigiLocker connected",
                        "Go back to the ScholarSetu app to choose the documents to import.", True)


@router.get("/me/digilocker/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str,
                      principal: StudentPrincipal = Depends(student_principal(MitraScope.UPLOAD_DOCUMENTS)),
                      service: DigiLockerService = Depends(get_digilocker_service)):
    """The session status; once connected, the student's issued documents."""
    try:
        session = await service.get_session(session_id, principal.student_id)
        documents = await service.list_documents(session) if session.status == "CONNECTED" else []
    except DigiLockerError as exc:
        await service.db.commit()  # keep a session marked FAILED by an expired token
        raise _http(exc)
    return SessionResponse(session_id=session.id, status=session.status, error=session.error,
                           digilocker_name=session.digilocker_name,
                           documents=[IssuedDocument(**d) for d in documents], **_mode())


@router.post("/me/digilocker/sessions/{session_id}/import", response_model=ImportResponse, status_code=201)
async def import_documents(session_id: str, body: ImportRequest,
                           principal: StudentPrincipal = Depends(student_principal(MitraScope.UPLOAD_DOCUMENTS)),
                           service: DigiLockerService = Depends(get_digilocker_service),
                           store=Depends(get_object_store)):
    """Import the chosen documents into the wallet. The DigiLocker token is discarded afterwards."""
    try:
        session = await service.get_session(session_id, principal.student_id)
        docs = await service.import_documents(session, body.uris, principal.user, WalletService(service.db, store))
    except DigiLockerError as exc:
        raise _http(exc)
    except StorageUnavailable:
        raise HTTPException(status_code=503, detail="Document storage is unavailable; try again later")
    await service.db.commit()
    return ImportResponse(imported=[to_response(d) for d in docs])


# ── Test DigiLocker sign-in page (mock mode only) ───────────────────────────────
# The mock runs on a private network; the student's browser reaches its sign-in page through here.

_AUTHORIZE_PATH = "/public/oauth2/1/authorize"


def _mock_only() -> None:
    if settings.DIGILOCKER_MODE != "mock":
        raise HTTPException(status_code=404, detail="Not Found")


def _relay(res: httpx.Response) -> Response:
    if res.status_code in (301, 302, 303, 307, 308):
        return RedirectResponse(res.headers["location"], status_code=302)
    return Response(content=res.content, status_code=res.status_code,
                    media_type=res.headers.get("content-type", "text/html"))


@router.get("/digilocker-test/authorize", include_in_schema=False)
async def test_authorize_page(request: Request, http: httpx.AsyncClient = Depends(get_digilocker_http)):
    _mock_only()
    try:
        return _relay(await http.get(_AUTHORIZE_PATH, params=list(request.query_params.multi_items())))
    except httpx.TransportError:
        return _result_page("Test DigiLocker unavailable", "The test DigiLocker could not be reached. Try again.",
                            False)


@router.post("/digilocker-test/authorize", include_in_schema=False)
async def test_authorize_submit(request: Request, http: httpx.AsyncClient = Depends(get_digilocker_http)):
    _mock_only()
    form = await request.form()
    try:
        return _relay(await http.post(_AUTHORIZE_PATH, data={k: str(v) for k, v in form.multi_items()}))
    except httpx.TransportError:
        return _result_page("Test DigiLocker unavailable", "The test DigiLocker could not be reached. Try again.",
                            False)
