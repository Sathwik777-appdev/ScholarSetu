"""In-process Mock DigiLocker Transport for development, demos, and cloud deployments.

Emulates the MeriPehchaan / DigiLocker partner OAuth 2.0 PKCE flow in-memory when
DIGILOCKER_MODE=mock, so the platform can run without needing a secondary mock service container.
"""

import base64
import hashlib
import html
import secrets
import time
from urllib.parse import parse_qs, urlencode

import httpx

TEST_CODE = "123456"
_MOCK_CODES: dict[str, dict] = {}
_MOCK_TOKENS: dict[str, dict] = {}

SUNITA_ISSUED_ITEMS = [
    {
        "name": "Marksheet 10",
        "type": "file",
        "size": "",
        "date": "",
        "parent": "",
        "mime": ["application/pdf"],
        "uri": "in.gov.jac-MARKSHEET_10-2026-109283",
        "doctype": "MARKSHEET_10",
        "description": "Class 10 (Matriculation) Marksheet",
        "issuerid": "Jharkhand Academic Council",
        "issuer": "Jharkhand Academic Council",
    },
    {
        "name": "Income Certificate",
        "type": "file",
        "size": "",
        "date": "",
        "parent": "",
        "mime": ["application/pdf"],
        "uri": "in.gov.jharkhand-INCER-JH/INC/2026/55120",
        "doctype": "INCOME_CERTIFICATE",
        "description": "Income Certificate",
        "issuerid": "Revenue Department, Jharkhand",
        "issuer": "Revenue Department, Jharkhand",
    },
    {
        "name": "Domicile Certificate",
        "type": "file",
        "size": "",
        "date": "",
        "parent": "",
        "mime": ["application/pdf"],
        "uri": "in.gov.jharkhand-DOMCR-JH/DOM/2021/1044",
        "doctype": "DOMICILE_CERTIFICATE",
        "description": "Domicile Certificate",
        "issuerid": "Revenue Department, Jharkhand",
        "issuer": "Revenue Department, Jharkhand",
    },
]


def _pdf(lines: list[str]) -> bytes:
    """A minimal, valid one-page PDF standing in for the issuer's signed document."""
    text = " ".join(f"({line.replace('(', '[').replace(')', ']')}) Tj T*" for line in lines)
    stream = f"BT /F1 12 Tf 14 TL 72 760 Td {text} ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = bytearray(b"%PDF-1.4\n"), []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def _render_page(body: str) -> str:
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>DigiLocker (TEST)</title>
<style>body{{font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;margin:0;background:#f4f6fb;color:#0f172a}}
.bar{{background:#b45309;color:#fff;padding:10px 16px;font-weight:600;font-size:14px;text-align:center}}
main{{max-width:440px;margin:32px auto;background:#fff;border-radius:16px;padding:28px;box-shadow:0 12px 32px -12px rgba(0,0,0,0.15)}}
h2{{margin-top:0;font-size:22px;color:#0f172a}}
label{{display:block;font-size:14px;margin-top:16px;font-weight:600;color:#334155}}
input{{width:100%;box-sizing:border-box;padding:12px;margin-top:6px;border:1.5px solid #cbd5e1;border-radius:10px;font-size:16px;font-family:monospace}}
input:focus{{border-color:#2563eb;outline:none}}
button{{margin-top:22px;width:100%;padding:13px;border:0;border-radius:10px;background:#0c1326;color:#fff;font-size:16px;font-weight:600;cursor:pointer}}
button:hover{{background:#1e293b}}
.card{{background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:14px;margin-top:16px;font-size:13px;line-height:1.5}}
.muted{{color:#64748b;font-size:13px}}
</style></head><body><div class="bar">TEST SERVICE: not the real DigiLocker. Documents here are test data.</div>
<main>{body}</main></body></html>"""


def mock_digilocker_handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path

    # 1. Authorize GET (renders mock DigiLocker sign-in page)
    if path.endswith("/public/oauth2/1/authorize") and request.method == "GET":
        params = dict(request.url.params)
        hidden = "".join(f'<input type="hidden" name="{k}" value="{html.escape(v)}">' for k, v in params.items())
        body = f"""<h2>Sign in to DigiLocker (test)</h2>
<p class="muted">ScholarSetu is requesting access to your verified student records.</p>
<div class="card">
  <strong>Demo Student Profile:</strong><br>
  Name: Sunita Hansda<br>
  Mobile: <code>9876543210</code><br>
  Aadhaar Ref: <code>AREF-JH-0004912</code><br>
  Test OTP: <code>123456</code>
</div>
<form method="post">{hidden}
<label>Mobile number<input name="mobile" inputmode="numeric" pattern="[0-9]{{10}}" value="9876543210" required></label>
<label>Code (OTP)<input name="otp" inputmode="numeric" pattern="[0-9]{{6}}" value="123456" required></label>
<button type="submit">Allow ScholarSetu to read my documents</button></form>"""
        return httpx.Response(200, headers={"content-type": "text/html; charset=utf-8"}, text=_render_page(body))

    # 2. Authorize POST (submits OTP, creates auth code, redirects with ?code=&state=)
    if path.endswith("/public/oauth2/1/authorize") and request.method == "POST":
        data = parse_qs(request.content.decode("utf-8"))
        redirect_uri = data.get("redirect_uri", ["scholarsetu://digilocker-callback"])[0]
        state = data.get("state", [""])[0]
        code_challenge = data.get("code_challenge", [""])[0]
        mobile = data.get("mobile", ["9876543210"])[0]
        otp = data.get("otp", ["123456"])[0]

        if otp != TEST_CODE:
            return httpx.Response(401, headers={"content-type": "text/html; charset=utf-8"},
                                  text=_render_page("<h2>Sign-in failed</h2><p>Wrong code. The test code is 123456.</p>"))

        code = f"mock-auth-code-{secrets.token_urlsafe(16)}"
        _MOCK_CODES[code] = {
            "mobile": mobile,
            "challenge": code_challenge,
            "expires": time.time() + 600,
        }
        dest = f"{redirect_uri}?{urlencode({'code': code, 'state': state})}"
        return httpx.Response(302, headers={"location": dest})

    # 3. Token exchange POST (code + PKCE verifier -> access token & identity profile)
    if path.endswith("/public/oauth2/1/token") and request.method == "POST":
        data = parse_qs(request.content.decode("utf-8"))
        code = data.get("code", [""])[0]
        code_verifier = data.get("code_verifier", [""])[0]

        grant = _MOCK_CODES.pop(code, None)
        # Even if grant was consumed or created in previous attempt, accept and map to Sunita Hansda
        token = f"mock-access-token-{secrets.token_urlsafe(24)}"
        _MOCK_TOKENS[token] = {"mobile": "9876543210", "expires": time.time() + 3600}

        return httpx.Response(200, json={
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "files.issueddocs",
            "digilockerid": "TEST-AREF-JH-0004912",
            "name": "Sunita Hansda",
            "dob": "2008-04-12",
            "gender": "F",
            "eaadhaar": "AREF-JH-0004912",
            "apaar_id": "APAAR-JH-2026-0812",
        })

    # 4. Issued files list GET
    if path.endswith("/public/oauth2/2/files/issued") and request.method == "GET":
        return httpx.Response(200, json={"items": SUNITA_ISSUED_ITEMS, "resource": "issued"})

    # 5. Document file GET
    if "/public/oauth2/1/file/" in path and request.method == "GET":
        doc_uri = path.split("/public/oauth2/1/file/")[-1]
        pdf_bytes = _pdf([
            "TEST DOCUMENT - NOT VALID - ScholarSetu test DigiLocker",
            "Issuer: Government of Jharkhand / JAC",
            f"Document URI: {doc_uri}",
            "Holder: SUNITA HANSDA (ST Category)",
        ])
        return httpx.Response(200, headers={"content-type": "application/pdf"}, content=pdf_bytes)

    # 6. Direct lookup by Aadhaar reference (for prototype verification mesh)
    if "/issued/" in path and request.method == "GET":
        return httpx.Response(200, json={
            "doc_type": "CASTE_CERTIFICATE",
            "holder_name": "Sunita Hansda",
            "holder_dob": "2008-04-12",
            "gender": "FEMALE",
            "district": "Dumka",
            "category": "ST",
            "tribe": "Santal",
            "status": "VALID",
        })

    return httpx.Response(404, json={"detail": "Not found in mock DigiLocker"})


def get_mock_digilocker_transport() -> httpx.MockTransport:
    return httpx.MockTransport(mock_digilocker_handler)
