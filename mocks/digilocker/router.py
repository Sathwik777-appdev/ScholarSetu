"""Mock DigiLocker (TEST ONLY).

Two surfaces:
- /issued/...: a direct lookup by Aadhaar reference, used by the verification mesh in the prototype.
- /public/oauth2/...: the authorised-partner flow, shaped like DigiLocker's partner API, so the platform's
  client is the same one the real service would use:
    GET/POST  /public/oauth2/1/authorize     sign-in and consent page, then redirect with ?code&state
    POST      /public/oauth2/1/token         code + PKCE verifier -> access token
    GET       /public/oauth2/2/files/issued  the signed-in person's issued documents
    GET       /public/oauth2/1/file/{uri}    one document (a PDF stamped TEST DOCUMENT)
  The registered test client is DIGILOCKER_CLIENT_ID / DIGILOCKER_CLIENT_SECRET (environment). Sign-in uses
  the person's mobile number and the fixed test code shown on the page. Codes and tokens live in memory.
"""

import base64
import hashlib
import html
import os
import secrets
import time
from urllib.parse import urlencode

from fastapi import APIRouter, Form, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from synthetic_data import db, get_student

router = APIRouter()

TEST_CODE = "123456"
_CODES: dict[str, dict] = {}    # auth code -> {aadhaar, client_id, redirect_uri, challenge, expires}
_TOKENS: dict[str, dict] = {}   # access token -> {aadhaar, expires}


@router.get("/issued/{aadhaar_ref}")
def get_issued_document(aadhaar_ref: str, doc_type: str):
    """An issuer-pushed document from the person's DigiLocker. 404 when absent."""
    student = get_student(aadhaar_ref)
    docs = student["sources"].get("digilocker", {}) if student else {}
    if doc_type not in docs:
        raise HTTPException(status_code=404, detail="NOT_FOUND")
    doc = docs[doc_type]
    return {"doc_type": doc_type, "holder_dob": student["dob"], "gender": student["gender"],
            "district": student["district"], **doc}


def _pdf(lines: list[str]) -> bytes:
    """A minimal, valid one-page PDF standing in for the issuer's signed document."""
    text = " ".join(f"({line.replace('(', '[').replace(')', ']')}) Tj T*" for line in lines)
    stream = f"BT /F1 12 Tf 14 TL 72 760 Td {text} ET".encode()
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
               b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
               b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offsets = bytearray(b"%PDF-1.4\n"), []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def _test_pdf(doc_type: str, doc: dict) -> bytes:
    lines = ["TEST DOCUMENT - NOT VALID - ScholarSetu test DigiLocker", doc["issuer"],
             f"{doc_type} {doc['doc_id']}", f"Holder: {doc['holder_name']}"]
    return _pdf(lines + [f"{k}: {v}" for k, v in doc.get("data", {}).items()])


@router.get("/issued/{aadhaar_ref}/file")
def get_issued_file(aadhaar_ref: str, doc_type: str):
    doc = get_issued_document(aadhaar_ref, doc_type)
    return Response(content=_test_pdf(doc_type, doc), media_type="application/pdf")


# ── Partner API (OAuth 2.0 authorisation code + PKCE) ───────────────────────────


def _client_ok(client_id: str, secret: str | None = None) -> bool:
    expected_id = os.environ.get("DIGILOCKER_CLIENT_ID")
    if not expected_id or client_id != expected_id:
        return False
    return secret is None or secrets.compare_digest(secret, os.environ.get("DIGILOCKER_CLIENT_SECRET", ""))


def _page(body: str, status: int = 200) -> HTMLResponse:
    return HTMLResponse(status_code=status, content=f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>DigiLocker (TEST)</title>
<style>body{{font-family:system-ui,sans-serif;margin:0;background:#f4f6fb;color:#0f172a}}
.bar{{background:#b45309;color:#fff;padding:10px 16px;font-weight:600;font-size:14px}}
main{{max-width:420px;margin:24px auto;background:#fff;border-radius:16px;padding:24px;box-shadow:0 8px 24px -12px #0003}}
label{{display:block;font-size:14px;margin-top:14px}} input{{width:100%;box-sizing:border-box;padding:12px;margin-top:6px;
border:1px solid #cbd5e1;border-radius:10px;font-size:16px}} button{{margin-top:18px;width:100%;padding:12px;border:0;
border-radius:10px;background:#0c1326;color:#fff;font-size:16px;font-weight:600}} .muted{{color:#64748b;font-size:13px}}
</style></head><body><div class="bar">TEST SERVICE: not the real DigiLocker. Documents here are test data.</div>
<main>{body}</main></body></html>""")


def _check_request(response_type: str, client_id: str, redirect_uri: str, state: str,
                   code_challenge: str, code_challenge_method: str) -> str | None:
    if response_type != "code":
        return "response_type must be 'code'"
    if not _client_ok(client_id):
        return "Unknown client_id"
    if not redirect_uri.startswith(("https://", "http://localhost", "http://127.0.0.1", "http://test")):
        return "redirect_uri must use https"
    if not state or not code_challenge or code_challenge_method != "S256":
        return "state and an S256 code_challenge (PKCE) are required"
    return None


@router.get("/public/oauth2/1/authorize", response_class=HTMLResponse)
def authorize_page(response_type: str = "", client_id: str = "", redirect_uri: str = "", state: str = "",
                   code_challenge: str = "", code_challenge_method: str = ""):
    problem = _check_request(response_type, client_id, redirect_uri, state, code_challenge, code_challenge_method)
    if problem:
        return _page(f"<h2>Request refused</h2><p>{html.escape(problem)}</p>", 400)
    hidden = "".join(f'<input type="hidden" name="{k}" value="{html.escape(v)}">' for k, v in {
        "response_type": response_type, "client_id": client_id, "redirect_uri": redirect_uri, "state": state,
        "code_challenge": code_challenge, "code_challenge_method": code_challenge_method}.items())
    return _page(f"""<h2 style="margin-top:0">Sign in to DigiLocker (test)</h2>
<p class="muted">ScholarSetu is asking to read your issued documents. You choose which ones to import next.</p>
<form method="post">{hidden}
<label>Mobile number<input name="mobile" inputmode="numeric" pattern="[0-9]{{10}}" required></label>
<label>Code<input name="otp" inputmode="numeric" pattern="[0-9]{{6}}" required></label>
<p class="muted">Test service: the code is {TEST_CODE}.</p>
<button type="submit">Allow ScholarSetu to read my documents</button></form>""")


@router.post("/public/oauth2/1/authorize")
def authorize_submit(response_type: str = Form(""), client_id: str = Form(""), redirect_uri: str = Form(""),
                     state: str = Form(""), code_challenge: str = Form(""), code_challenge_method: str = Form(""),
                     mobile: str = Form(""), otp: str = Form("")):
    problem = _check_request(response_type, client_id, redirect_uri, state, code_challenge, code_challenge_method)
    if problem:
        return _page(f"<h2>Request refused</h2><p>{html.escape(problem)}</p>", 400)
    person = next((s for s in db.get("students", []) if s.get("phone") == mobile), None)
    if person is None or otp != TEST_CODE:
        return _page("<h2>Could not sign in</h2><p>Unknown mobile number or wrong code.</p>"
                     "<p class='muted'>Go back and try again.</p>", 401)
    code = secrets.token_urlsafe(24)
    _CODES[code] = {"aadhaar": person["aadhaar"], "client_id": client_id, "redirect_uri": redirect_uri,
                    "challenge": code_challenge, "expires": time.time() + 300}
    return RedirectResponse(f"{redirect_uri}?{urlencode({'code': code, 'state': state})}", status_code=302)


@router.post("/public/oauth2/1/token")
def token(grant_type: str = Form(""), code: str = Form(""), client_id: str = Form(""),
          client_secret: str = Form(""), redirect_uri: str = Form(""), code_verifier: str = Form("")):
    grant = _CODES.pop(code, None)  # single use
    if grant_type != "authorization_code" or grant is None or grant["expires"] < time.time():
        return JSONResponse({"error": "invalid_grant"}, status_code=400)
    if not _client_ok(client_id, client_secret) or client_id != grant["client_id"] \
            or redirect_uri != grant["redirect_uri"]:
        return JSONResponse({"error": "invalid_client"}, status_code=401)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest()).rstrip(b"=").decode()
    if not secrets.compare_digest(challenge, grant["challenge"]):
        return JSONResponse({"error": "invalid_grant", "error_description": "PKCE verification failed"},
                            status_code=400)
    access = secrets.token_urlsafe(32)
    _TOKENS[access] = {"aadhaar": grant["aadhaar"], "expires": time.time() + 3600}
    person = get_student(grant["aadhaar"])
    return {"access_token": access, "token_type": "Bearer", "expires_in": 3600, "scope": "files.issueddocs",
            "digilockerid": f"TEST-{grant['aadhaar']}", "name": f"{person['first_name']} {person['last_name']}",
            "dob": person["dob"], "gender": person["gender"][0]}


def _holder(authorization: str | None) -> dict | None:
    grant = _TOKENS.get((authorization or "").removeprefix("Bearer ").strip())
    if grant is None or grant["expires"] < time.time():
        return None
    return get_student(grant["aadhaar"])


@router.get("/public/oauth2/2/files/issued")
def issued_files(authorization: str | None = Header(None)):
    person = _holder(authorization)
    if person is None:
        return JSONResponse({"error": "invalid_token"}, status_code=401)
    items = [{"name": doc_type.replace("_", " ").title(), "type": "file", "size": "", "date": "", "parent": "",
              "mime": ["application/pdf"], "uri": doc["doc_id"], "doctype": doc_type,
              "description": doc_type.replace("_", " ").title(), "issuerid": doc["issuer"], "issuer": doc["issuer"]}
             for doc_type, doc in person["sources"].get("digilocker", {}).items()]
    return {"items": items, "resource": "issued"}


@router.get("/public/oauth2/1/file/{uri:path}")
def issued_file(uri: str, authorization: str | None = Header(None)):
    person = _holder(authorization)
    if person is None:
        return JSONResponse({"error": "invalid_token"}, status_code=401)
    for doc_type, doc in person["sources"].get("digilocker", {}).items():
        if doc["doc_id"] == uri:
            return Response(content=_test_pdf(doc_type, doc), media_type="application/pdf",
                            headers={"Content-Disposition": f'inline; filename="{doc_type}.pdf"'})
    return JSONResponse({"error": "not_found"}, status_code=404)
