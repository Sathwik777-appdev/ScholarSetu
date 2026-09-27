"""Demo smoke test: the eight scenes of ARCHITECTURE.md §14, checked by content against a running stack.

Run it against a freshly seeded demo stack (DEMO_MODE=true, `python scripts/seed_demo.py` in the core
container). It exits 1 if any assertion fails and prints "ALL 8 SCENES PASSED" only when every one passed.

Environment:
  SMOKE_BASE_URL     API origin (default http://localhost:8000)
  DEMO_OTP           the demo login code (default 123456; demo users only, DEMO_MODE only)
  SMS_GATEWAY_TOKEN  the simulated SMS gateway's shared secret (for Scene 6)

Standard library only, so it runs anywhere.
"""

import json
import os
import re
import sys
import traceback
import urllib.error
import urllib.parse
import urllib.request
import uuid

BASE = os.environ.get("SMOKE_BASE_URL", "http://localhost:8000").rstrip("/")
DEMO_OTP = os.environ.get("DEMO_OTP", "123456")
SMS_TOKEN = os.environ.get("SMS_GATEWAY_TOKEN", "")
PHONES = {"sunita": "9876543210", "rahul": "9876543211", "guardian": "9876543212",
          "district": "9876543230", "ministry": "9876543240"}
RUPEES = re.compile(r"(?:Rs|₹)\s?([\d,]+(?:\.\d+)?)")


class Check(AssertionError):
    pass


def expect(condition, message):
    if not condition:
        raise Check(message)


def call(method, path, body=None, token=None, headers=None, query=None, raw=False):
    url = f"{BASE}{path}" + (f"?{urllib.parse.urlencode(query)}" if query else "")
    h = {"Content-Type": "application/json", **(headers or {})}
    if token:
        h["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode()
            return resp.status, (text if raw else (json.loads(text) if text else None))
    except urllib.error.HTTPError as e:
        text = e.read().decode()
        try:
            return e.code, json.loads(text)
        except ValueError:
            return e.code, text
    except urllib.error.URLError as e:
        raise Check(f"cannot reach {url}: {e.reason}") from e


_tokens = {}


def login(who):
    if who not in _tokens:
        call("POST", "/v1/auth/otp/request", {"phone": PHONES[who]})
        status, body = call("POST", "/v1/auth/otp/verify", {"phone": PHONES[who], "otp": DEMO_OTP})
        expect(status == 200, f"login as {who} failed ({status}): {body}")
        _tokens[who] = body["access_token"]
    return _tokens[who]


def ok(status, body, what):
    expect(200 <= status < 300, f"{what}: HTTP {status}: {body}")
    return body


state = {}


# ── scenes ────────────────────────────────────────────────────────────────────


def scene_1_family_mode():
    """Father sees both children, with amounts from the ledger."""
    home = ok(*call("GET", "/v1/me/household", token=login("guardian")), "household")
    kids = {s["student"]["name"]: s for s in home["students"]}
    expect({"Sunita Hansda", "Rahul Hansda"} <= kids.keys(), f"children shown: {list(kids)}")
    rahul = kids["Rahul Hansda"]
    expect(rahul["applications"][0]["scheme"] == "PRE_MATRIC", "Rahul's scheme")
    expect(rahul["applications"][0]["current_state"] == "CREDITED", "Rahul's Pre-Matric is credited")
    money = ok(*call("GET", "/v1/me/payments", token=login("rahul")), "Rahul's payments")
    expect(rahul["total_received"] == money["total_credited"] > 0,
           f"family view shows {rahul['total_received']}, ledger says {money['total_credited']}")
    sunita = kids["Sunita Hansda"]["applications"][0]
    state["sunita_app"] = sunita["id"]
    state["rahul_money"] = money
    return f"{len(kids)} children; Rahul received ₹{money['total_credited']:,.0f} (matches ledger)"


def scene_2_pathway():
    """The pathway comes from the ledger; nothing is suggested without verified facts."""
    p = ok(*call("GET", "/v1/me/pathway", token=login("sunita")), "Sunita's pathway")
    expect(p["current_scheme"] == "POST_MATRIC" and p["current_application_id"] == state["sunita_app"],
           f"current rung: {p}")
    expect(p["ladder"][p["ladder_position"]] == "POST_MATRIC", "ladder position")
    r = ok(*call("GET", "/v1/me/pathway", token=login("rahul")), "Rahul's pathway")
    expect(r["current_scheme"] == "PRE_MATRIC", f"Rahul's rung: {r}")
    return f"Sunita on {p['current_scheme']} (rung {p['ladder_position'] + 1}/5); Rahul on {r['current_scheme']}"


def scene_3_verification_mesh():
    """Sources are queried with consent; 'Hansdah' is explained and provisional; the application continues."""
    sunita = login("sunita")
    claims = ["IDENTITY", "INCOME", "ST_STATUS"]
    consent = ok(*call("POST", "/v1/consents", {"requester": "SCHOLARSETU_VERIFICATION_MESH",
                                               "purpose": "Scholarship eligibility verification",
                                               "data_items": claims, "duration_days": 30}, token=sunita), "consent")
    report = ok(*call("POST", "/v1/verify/claims", {"application_id": state["sunita_app"], "required_claims": claims,
                                                    "consent_id": consent["id"]}, token=sunita), "verify")
    by_claim = {c["claim_type"]: c for c in report["claims"]}
    st = by_claim["ST_STATUS"]
    expect(st["status"] == "PROVISIONAL" and st["review_case_id"], f"ST_STATUS should be provisional: {st}")
    expect("hansdah" in json.dumps(st).lower(), "the explanation should name the Hansda/Hansdah difference")
    expect(by_claim["IDENTITY"]["status"] == "VERIFIED", f"identity: {by_claim['IDENTITY']['status']}")
    app = ok(*call("GET", f"/v1/applications/{state['sunita_app']}", token=sunita), "application")
    expect(app["canonical_state"] not in ("REJECTED", "DEFICIENCY_RAISED"), f"application stopped: {app['canonical_state']}")
    state["case_id"] = st["review_case_id"]
    return f"IDENTITY {by_claim['IDENTITY']['status']}, INCOME {by_claim['INCOME']['status']}, ST_STATUS PROVISIONAL (case opened); application still {app['canonical_state']}"


def scene_4_dbt_guardian():
    """The bank account is not Aadhaar-seeded: the check fails with steps in Hindi."""
    check = ok(*call("POST", f"/v1/dbt/health-check/{state['sunita_app']}", token=login("sunita")), "DBT check")
    expect(check["overall_status"] != "PASS", f"DBT check must not pass: {check['overall_status']}")
    codes = [i["code"] for i in check["issues"]]
    expect(any("SEED" in c for c in codes), f"expected an Aadhaar-seeding issue, got {codes}")
    issue = next(i for i in check["issues"] if "SEED" in i["code"])
    expect(issue["message_hi"] and issue["fix_steps_hi"], "Hindi message and steps")
    return f"{check['overall_status']}: {issue['code']} — {issue['message_hi'][:40]}…"


def scene_5_jago():
    """'Mera paisa kab aayega?' is answered from the ledger."""
    money = state["rahul_money"]
    answer = ok(*call("POST", "/v1/jago/chat", {"message": "Mera paisa kab aayega?", "language": "hi"},
                      token=login("rahul")), "JAGO")
    quoted = {float(m.replace(",", "")) for m in RUPEES.findall(answer["response_text"])}
    ledger = {money["total_sanctioned"], money["total_credited"], money["total_pending"], money["total_failed"]}
    ledger |= {i["amount"] for a in money["applications"] for i in a["instalments"]}
    expect(answer["intent"] == "payment_info", f"intent {answer['intent']}")
    expect(quoted and quoted <= ledger, f"JAGO quoted {quoted}, ledger has {ledger}")
    sunita = ok(*call("POST", "/v1/jago/chat", {"message": "Mera paisa kab aayega?", "language": "hi"},
                      token=login("sunita")), "JAGO (Sunita)")
    expect(not RUPEES.search(sunita["response_text"]), "no amount may be invented before sanction")
    return f"Rahul: amounts {sorted(quoted)} all in the ledger; Sunita: no invented amount"


def scene_6_offline_and_sms():
    """An action queued offline is applied once on reconnect; delta sync works; SMS STATUS answers."""
    sunita = login("sunita")
    notes = ok(*call("GET", "/v1/notifications", token=sunita), "notifications")
    key = f"smoke-{uuid.uuid4()}"
    item = {"idempotency_key": key, "action": "MARK_NOTIFICATION_READ",
            "payload": {"notification_id": notes[0]["id"] if notes else "none"}}
    first = ok(*call("POST", "/v1/sync/outbox", {"items": [item]}, token=sunita), "outbox")["results"][0]
    again = ok(*call("POST", "/v1/sync/outbox", {"items": [item]}, token=sunita), "outbox resend")["results"][0]
    expect(first["status"] in ("APPLIED", "REJECTED"), f"first send: {first}")
    expect(again["status"] == "DUPLICATE" and again["original_status"] == first["status"], f"resend: {again}")
    page = ok(*call("GET", "/v1/sync", token=sunita, query={"cursor": 0}), "sync")
    expect(page["events"] and all(e["application_id"] == state["sunita_app"] for e in page["events"]),
           "delta sync returns only Sunita's events")
    expect(SMS_TOKEN, "SMS_GATEWAY_TOKEN is not set")
    status, _ = call("POST", "/v1/sms/inbound", {"from_phone": PHONES["sunita"], "body": f"STATUS {state['sunita_app']}"},
                     headers={"X-SMS-Gateway-Token": SMS_TOKEN})
    expect(status == 200, f"SMS STATUS: HTTP {status}")
    status, _ = call("POST", "/v1/sms/inbound", {"from_phone": "9000000123", "body": f"STATUS {state['sunita_app']}"},
                     headers={"X-SMS-Gateway-Token": SMS_TOKEN})
    expect(status == 403, f"unregistered phone must be refused, got {status}")
    status, page_html = call("GET", "/v1/dev/sms-outbox", raw=True)
    expect(status == 200 and state["sunita_app"] in page_html, "the STATUS reply should name the application")
    return f"outbox {first['status']} then DUPLICATE; {len(page['events'])} events synced; SMS reply sent, stranger refused"


def scene_7_officer_console():
    """The officer approves the explained case; the decision is in the ledger and the chain verifies."""
    officer = login("district")
    cases = ok(*call("GET", "/v1/review/cases", token=officer, query={"status": "PENDING"}), "review queue")
    case = next((c for c in cases if c["id"] == state.get("case_id")), None)
    expect(case is not None, "the case from Scene 3 is in the district queue")
    expect(case["explanation"] and case["identity_score"] is not None, "score and explanation shown")
    decided = ok(*call("POST", f"/v1/review/cases/{case['id']}/decision",
                       {"decision": "APPROVE", "notes": "Hansdah is the same family name; certificate checked"},
                       token=officer), "decision")
    event_id = decided["ledger_event_id"]
    again = ok(*call("GET", "/v1/review/cases", token=officer, query={"status": "APPROVED"}), "refetch")
    expect(any(c["id"] == case["id"] and c["decision_event_id"] == event_id for c in again), "decision persisted")
    timeline = ok(*call("GET", f"/v1/applications/{state['sunita_app']}/timeline", token=login("sunita")), "timeline")
    expect(any(e["event_id"] == event_id for e in timeline), "Sunita's timeline shows the decision")
    chain = ok(*call("GET", f"/v1/applications/{state['sunita_app']}/verify-chain", token=officer), "verify-chain")
    expect(chain["valid"] is True, f"hash chain: {chain}")
    return f"approved (score {case['identity_score']:.2f}); ledger event {event_id}; chain valid over {chain['events_checked']} events"


def scene_8_reach_radar():
    """Coverage is computed by privacy-preserving linkage; conversion by district."""
    ministry = login("ministry")
    report = ok(*call("GET", "/v1/analytics/coverage", token=ministry, query={"level": "district"}), "coverage")
    expect(report["rows"], "coverage rows")
    for row in report["rows"]:
        expected = round(100 * row["with_scholarship"] / row["enrolled_st"], 1) if row["enrolled_st"] else 0
        expect(abs(row["coverage_pct"] - expected) < 0.11, f"coverage arithmetic for {row['district']}: {row}")
    expect(report["matched_by_apaar"] + report["matched_by_clk"] > 0, "linkage found matches")
    transitions = ok(*call("GET", "/v1/analytics/transitions", token=ministry), "transitions")
    expect(transitions, "transition rows")
    status, _ = call("GET", "/v1/analytics/coverage", token=login("sunita"))
    expect(status == 403, "students cannot see ministry analytics")
    low = min(report["rows"], key=lambda r: r["coverage_pct"])
    return f"{len(report['rows'])} districts; lowest {low['district']} {low['coverage_pct']}%; {report['method']}"


SCENES = [scene_1_family_mode, scene_2_pathway, scene_3_verification_mesh, scene_4_dbt_guardian, scene_5_jago,
          scene_6_offline_and_sms, scene_7_officer_console, scene_8_reach_radar]


def main() -> int:
    try:
        status, health = call("GET", "/health/ready")
    except Check as exc:
        print(exc)
        return 1
    if status != 200:
        print(f"API not ready at {BASE}: HTTP {status} {health}")
        return 1
    results = []
    for n, scene in enumerate(SCENES, start=1):
        try:
            detail = scene()
            results.append((n, True, detail))
            print(f"PASS  Scene {n}: {scene.__doc__.strip()}\n      {detail}")
        except Check as exc:
            results.append((n, False, str(exc)))
            print(f"FAIL  Scene {n}: {scene.__doc__.strip()}\n      {exc}")
        except Exception as exc:  # a crash is a failure too, never a pass
            results.append((n, False, repr(exc)))
            print(f"ERROR Scene {n}: {scene.__doc__.strip()}\n      {exc!r}")
            traceback.print_exc(limit=2)
    failed = [n for n, passed, _ in results if not passed]
    print()
    if failed:
        print(f"{len(failed)} of {len(SCENES)} scenes FAILED: {failed}")
        return 1
    print(f"ALL {len(SCENES)} SCENES PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
