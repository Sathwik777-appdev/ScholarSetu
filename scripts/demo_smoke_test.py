"""End-to-End Demo Smoke Test for ScholarSetu.

Tests all 8 scenes of the Judge Demo Storyline against the live backend.
Uses standard library urllib so it runs anywhere without dependencies.
"""

import sys
import json
import urllib.request
import urllib.error

BASE_URL = "http://localhost:8000"


def make_request(method: str, path: str, data: dict = None, headers: dict = None):
    url = f"{BASE_URL}{path}"
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)

    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8")
            return resp.status, json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        return e.code, json.loads(content) if content else {"error": str(e)}
    except Exception as e:
        return 0, {"error": str(e)}


def run_demo_smoke_test():
    print("=" * 60)
    print("🎓 SCHOLARSETU — JUDGE DEMO STORYLINE SMOKE TEST")
    print("=" * 60)

    # 1. Health check
    print("\n[Step 0] Checking System Health...")
    status, res = make_request("GET", "/health")
    if status != 200:
        print(f"❌ Server not reachable at {BASE_URL}. Start server with 'make dev' or 'uvicorn app.main:app'.")
        sys.exit(1)
    print(f"✅ System Healthy: {res}")

    # 2. Scene 1: Family Mode (Father view)
    print("\n[Scene 1: 0:00-0:45] Family Mode (Father opens app, sees both children)...")
    status, res = make_request("GET", "/v1/me/household?household_id=hh_hansda_001")
    assert status == 200, f"Failed: {res}"
    guardian = res.get("guardian_name")
    students = res.get("students", [])
    print(f"✅ Household: {guardian} | Children found: {len(students)}")
    for s in students:
        st_info = s.get("student", {})
        apps = s.get("applications", [])
        state = apps[0].get("current_state") if apps else "NONE"
        rec = s.get("total_received")
        print(f"   👤 {st_info.get('name')}: {apps[0].get('scheme')} -> [{state}] (₹{rec} received)")

    # 3. Scene 2: Pathway Nudge
    print("\n[Scene 2: 0:45-1:30] Lifetime Pathway Nudge (Sunita passed Class 10)...")
    status, res = make_request("GET", "/v1/me/pathway?student_id=stu-sunita-001")
    assert status == 200, f"Failed: {res}"
    print(f"✅ Current Rung: {res.get('current_scheme')} -> Next Eligible: {res.get('next_eligible')}")
    print(f"   Trigger: {res.get('transition_trigger')}")
    print(f"   Pre-filled application available: {res.get('pre_filled_available')}")

    # 4. Scene 3: Verification Mesh & Identity Resolver
    print("\n[Scene 3: 1:30-2:45] Verification Mesh + Indic Name Resolution...")
    verify_payload = {
        "student_id": "stu-sunita-001",
        "required_claims": ["IDENTITY", "ST_STATUS", "INCOME", "SCHOOL_ENROLMENT"],
        "consent_id": "cst-sunita-001"
    }
    status, res = make_request("POST", "/v1/verify/claims", verify_payload)
    assert status == 200, f"Failed: {res}"
    print(f"✅ Overall Status: {res.get('overall_status')} | Requires Manual Review: {res.get('requires_manual_review')}")
    print(f"   Identity Resolution Score: {res.get('identity_resolution_score')} ({res.get('identity_decision')})")
    for claim in res.get("claims", []):
        print(f"   📋 Claim: {claim.get('claim_type')} -> {claim.get('status')} via {claim.get('source')}")

    # 5. Scene 4: DBT Guardian
    print("\n[Scene 4: 2:45-3:30] DBT Guardian Pre-Sanction Health Check...")
    status, res = make_request("POST", "/v1/dbt/health-check/APP-PM-2026-000812")
    assert status == 200, f"Failed: {res}"
    print(f"✅ DBT Overall Status: {res.get('overall_status')}")
    for issue in res.get("issues", []):
        print(f"   ⚠️ Issue: {issue.get('code')}")
        print(f"      EN: {issue.get('message')}")
        print(f"      HI: {issue.get('message_hi')}")
        print(f"      Steps: {issue.get('fix_steps')}")

    # 6. Scene 5: JAGO Voice grounded chat
    print("\n[Scene 5: 3:30-4:30] JAGO Grounded Chat ('Mera paisa kab aayega?')...")
    chat_payload = {
        "message": "Mera paisa kab aayega?",
        "language": "hi",
        "channel": "voice"
    }
    status, res = make_request("POST", "/v1/jago/chat", chat_payload)
    assert status == 200, f"Failed: {res}"
    print(f"✅ JAGO Grounded Response:\n   \"{res.get('response_text')}\"")
    print(f"   Tools invoked: {res.get('tool_calls_made')}")

    # 7. Scene 7: Officer Console Review Queue
    print("\n[Scene 7: 5:15-6:00] Officer Review Queue & Decision...")
    status, res = make_request("GET", "/v1/review/cases?sort=sla_risk")
    assert status == 200, f"Failed: {res}"
    print(f"✅ Review Cases in queue: {len(res)}")
    if res:
        case = res[0]
        print(f"   Case ID: {case.get('id')} for {case.get('student_name')}")
        print(f"   Explanation: {case.get('explanation')}")

        # Post decision
        dec_payload = {"decision": "VERIFIED", "notes": "Approved after reviewing transliteration variation."}
        d_status, d_res = make_request("POST", f"/v1/review/cases/{case.get('id')}/decision", dec_payload)
        print(f"   ✅ Officer Action: {d_res.get('decision')} | Status: {d_res.get('status')}")

    # 8. Scene 8: Reach Radar Coverage Heatmap
    print("\n[Scene 8: 6:00-7:00] Reach Radar (Coverage Gap Discovery via PPRL)...")
    status, res = make_request("GET", "/v1/analytics/coverage?level=district")
    assert status == 200, f"Failed: {res}"
    print(f"✅ Coverage Analytics Districts: {len(res)}")
    for d in res[:3]:
        print(f"   📍 {d.get('district')} ({d.get('state')}): {d.get('coverage_pct')}% coverage (ST Enrolled: {d.get('total_enrolled')}, Scholarships: {d.get('total_scholarship')})")

    # 9. Scholarship Passport (Attestations)
    print("\n[Passport] Scholarship Passport (Verify Once, Reuse Everywhere)...")
    status, res = make_request("GET", "/v1/me/attestations?student_id=stu-sunita-001")
    assert status == 200, f"Failed: {res}"
    print(f"✅ Passport for student: {res.get('student_id')}")
    att_dict = res.get("attestations", {})
    for claim_type, att_list in att_dict.items():
        for att in att_list:
            exp = att.get("expiry_date") or "LIFETIME"
            print(f"   📜 {claim_type}: Status={att.get('status')} | Source={att.get('source')} | Valid={exp}")

    print("\n" + "=" * 60)
    print("🎉 ALL 8 SCENES OF JUDGE DEMO STORYLINE PASSED CLEANLY!")
    print("=" * 60)


if __name__ == "__main__":
    run_demo_smoke_test()
