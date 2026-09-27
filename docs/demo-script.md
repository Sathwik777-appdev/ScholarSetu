# ScholarSetu — Judge Demo Script (about 7 minutes)

Each scene below is also checked automatically by `scripts/demo_smoke_test.py` (`make smoke-test`), so
what you show is what the tests prove. Run the smoke test on a *spare* seeded stack, not the one you demo
on: Scene 7 approves the review case, after which Scene 3 no longer opens one.

## Setup (before the judges arrive)

```bash
python3 scripts/make_env.py --demo && make keys   # first time only
make up && make seed
cd apps/console && npm run dev                    # console at http://localhost:5173
cd apps/mobile && flutter run                     # Android emulator
```

Demo login code for seeded accounts: `123456` (only with `DEMO_MODE=true`). Phone numbers are in the
README. Simulated SMS (including OTPs and STATUS replies): http://localhost:8000/v1/dev/sms-outbox

## Persona

**Sunita Hansda**, Dumka (Jharkhand), has applied for Post-Matric; her application is with the district
for verification. Her brother **Rahul** received his Pre-Matric scholarship. Their father **Babulal**
shares one phone. **Kavita Tudu**, the hostel warden, helps students as a Mitra.

---

### Scene 1 — Family mode (0:00–0:45)
App: sign in as Babulal (9876543212).
- Both children appear with each application's stage and next step.
- Rahul: Pre-Matric, **Money credited**, with the amount received — the same figure as Rahul's own Money tab (it comes from the ledger's payment records).

### Scene 2 — Scholarship pathway (0:45–1:15)
App: sign in as Sunita (9876543210), Home tab, "Your scholarship path".
- Current rung: Post-Matric (rung 2 of 5). No next scheme is suggested, because no verified fact puts her on another rung.
- Talking point: when a verified fact does (e.g. Class 11 enrolment for a Pre-Matric holder, or NET/JRF for a PhD scholar), the pathway engine prepares a pre-filled draft for the student to submit (covered by `tests/integration/test_phase6_eligibility.py`).

### Scene 3 — Verification mesh and the name mismatch (1:15–2:30)
API (Swagger at http://localhost:8000/docs, authorised as Sunita), or the smoke test output:
1. `POST /v1/consents` for IDENTITY, INCOME, ST_STATUS — verification needs the student's consent.
2. `POST /v1/verify/claims` — IDENTITY and INCOME are **verified** by UIDAI and e-District; ST_STATUS is **provisional**: the certificate says "Sunita Hansdah". The resolver's explanation names the trailing "h"; a review case is opened.
3. The application stays in district verification. Nothing was rejected.

### Scene 4 — DBT Guardian (2:30–3:15)
`POST /v1/dbt/health-check/{Sunita's application}`:
- Result **FAIL: AADHAAR_NOT_SEEDED** — her Aadhaar is not mapped to a bank account for government payments.
- The Hindi message and the fix steps (take Aadhaar to the bank and ask for DBT/NPCI seeding) are shown before any money is sent.

### Scene 5 — JAGO (3:15–4:00)
App, JAGO tab: ask "Mera paisa kab aayega?"
- As Rahul: the answer quotes his credited amount — the same number as the Money tab.
- As Sunita: nothing has been sanctioned yet, so JAGO gives no amount or date; it gives her application's stage.
- Ask "Post matric ki income limit kya hai?" — the answer quotes the guideline text and cites its source.

### Scene 6 — Offline and SMS (4:00–4:45)
1. App as Sunita: turn on airplane mode. The banner says the server cannot be reached and that you are seeing the saved copy ("Saved copy. Last updated …").
2. Passport tab → Upload a document: it is saved in the encrypted outbox; the banner shows "1 change … will be sent when the connection returns … NOT reached the office yet".
3. Airplane mode off → the outbox sends it once (idempotency key); the Sync screen empties.
4. Feature phone: the SMS gateway posts `STATUS <application id>` from Sunita's number → the reply (on the dev SMS page) gives her application's stage in Hindi. From an unregistered number → refused.

### Scene 7 — Officer console (4:45–5:45)
Console: sign in as the District Welfare Officer (9876543230).
- Review queue: Sunita's ST_STATUS case with the resolver's score, the explanation and the evidence from the source.
- Write a reason, **Approve** → the banner shows "Recorded in ledger" and the ledger event id (only after the API confirms).
- Open the application: the timeline shows the decision; "Ledger integrity" re-verifies the hash chain on the spot.

### Scene 8 — Reach Radar (5:45–7:00)
Console: sign in as the Ministry (9876543240).
- Coverage: enrolled ST students (synthetic UDISE+ roster) who hold a scholarship, by district and block, lowest first — found by privacy-preserving linkage (hashed APAAR IDs and Bloom-filter encodings), no names exchanged.
- Bottlenecks and SLA: where applications wait; DBT failures by district.
- Close: *verify once, reuse everywhere, and never lose a tribal student between schemes, systems or bank accounts.*

---

## If judges ask

- **Mitra mode:** app as Kavita (9876543220) → Mitra screen → student ID `stu-sunita-001`, "Check application status" → the code goes to *Sunita's* phone (dev SMS page); enter it → status view; End session.
- **Tamper detection:** change any field of a ledger event in Postgres, then `GET /v1/applications/{id}/verify-chain` → `valid: false` with the first altered event (`tests/integration/test_judge_probes.py::test_c...`).
- **Rules as code:** open `rules/post_matric_2026_v1.json` — every value carries its source and whether the team has verified it; see `docs/RULE_VALUES_TO_VERIFY.md` for values still to confirm.
- **Registration:** app → "New student? Register" → phone confirmed by SMS code → home shows **"Registered — application NOT submitted"** until an application is sent.
