# ScholarSetu — Workflow Audit

**Scope:** the whole product as a person uses it: students (app), guardians, helpers (Mitra), institute / district /
state officers and the Ministry (console), plus the cloud workflows underneath (wake and sleep, the VM, notifications).
**State audited:** `main` at `1b51e41`+ and the live deployment, 2026-10-02.

## 1. Method

- **Live end-to-end run (39 checks)** against the deployed API with the demo accounts: every endpoint each role
  uses, the data fields the app reads, DigiLocker sign-in and document import, a full deficiency loop across four
  roles with a notification through the VM, data-rights requests. 38 passed; the 39th was my wrong query name.
- **Every console page as every role** on the live site, in a real browser: no crashes, no failed requests.
- **Journeys run in the test harness** for the two paths that production students and officers would walk.
- **Code reading** for the gaps a script cannot show (no screen, no endpoint, no cleanup).
- The live demo data was restored to the clean seed afterwards (backup taken first).

## 2. What works

| Workflow | Result |
|---|---|
| Sign-in: demo accounts, DigiLocker (test), replay and wrong-code refusal; officers refused the demo code | Works |
| Ledger: apply → institute → district → deficiency → student reply with a document → institute → district | Works; the hash chain stayed valid (10 events) |
| Notifications: officer raises a deficiency → student notified through the VM (outbox → NATS → consumer) | Works, 5 seconds |
| SLA escalation: Temporal workflow → reminder to the district officer | Works |
| DigiLocker import: sign-in page, list, import, PDF stored, labelled "(test)", never "verified" | Works |
| Wallet privacy: another account cannot open a document | Works (403) |
| Role boundaries: institute officers refused analytics, district officers refused officer admin | Works |
| Data rights: request, officer sees and resolves it, export | Works |
| Console: every allowed page for all four roles; phone width without sideways scroll | Works |
| Wake on request, nightly sleep, power manager private | Works (3–8 minutes to wake) |
| VM: NATS, Temporal, Cloud SQL proxy, mocks, worker running; response times about 100 ms | Works |
| Tests: 507 backend, 10 app; CI file parses; dependency install against the lock succeeds | Pass |

## 3. Problems found

### Critical — a real person cannot complete the core journey

**W1. A student who signs up with DigiLocker cannot be verified.**
Registration creates the student with no Aadhaar reference and no APAAR ID, and every government source is looked up
by one of those. Running the journey: all five claims (identity, ST status, income, higher education, marksheets)
came back `MANUAL_REVIEW` with "No Aadhaar reference / No APAAR ID on the student record". Every real student would
need five manual review cases, and an officer approving one must type the value with no evidence.
*Fix:* link the DigiLocker identity to a vault reference at sign-up (the real service returns the Aadhaar-linked
identity with consent; the test DigiLocker already returns `TEST-<reference>`), and ask for the APAAR ID.

**W2. After a sanction, nothing ever pays.**
The officer sanctions; both instalments stay "Scheduled" forever. A portal sync changes nothing and no endpoint can
start a payment (the only payment actions are the retry of a failed one and the bank check). Payments for
applications created in ScholarSetu have no source that reports them.
*Fix:* decide who moves the money: either a PFMS payment feed for ScholarSetu sanctions (the mock PFMS already has
`initiate-payment`), or an officer "release payment" action that calls it and records the result in the ledger.

**W3. Sessions last 15 minutes with no refresh, and expiry wipes the phone.**
There is no refresh token. When one expires, the app signs out and deletes everything saved on the phone, including
offline actions not yet sent (an application queued offline is lost if the student comes back after 15 minutes).
Officers lose a half-filled sanction form the same way.
*Fix:* refresh tokens (or a longer, revocable session); on expiry keep the outbox and ask to sign in again.

### High

**W4. The bank check does not gate the sanction.** A sanction went through while the DBT check said FAIL
(Aadhaar not seeded). The design says to check "before sanction"; the endpoint does not look at it.

**W5. Guardians and helpers (Mitra) cannot exist for real people.** Only the seed creates them: DigiLocker sign-up
makes students, the Officers page enrols officers. Family mode and the helper flow are unreachable in production,
and new students are never attached to a household.

**W6. Signed passports claim a source that is test data.** The signed attestation says `source: UIDAI` and
`e-District` for answers that come from the synthetic test services; only DigiLocker is labelled "(test)". Anyone
scanning a passport QR would be told UIDAI verified it. *Fix:* label every result from the test services "(test)"
and put `test: true` in the signed payload, until real sources are connected.

**W7. AI phrasing is silently off.** The live server asks Google for `gemini-2.5-flash`; Google answers 404 ("no
longer available to new users, use gemini-3.8-flash"). The code's default is already `gemini-3.8-flash`, but
`deploy.sh` defaults to the old name, so any deploy that does not set it reverts it. (The stored key itself works.)
This is also why the key you pasted may have seemed to do nothing: the live secret is still the version of
2026-09-28, and neither `.env` file contains a key. *Fix:* correct the default in `deploy.sh` and `.env.example`;
store the new key as a new secret version.

### Medium

**W8. An officer's "more information needed" request cannot be answered.** The student sees it as a task but only
deficiencies have a Respond button, and there is no endpoint to answer one. The open case also blocks sanction.

**W9. Repeat wake requests time out.** While the database is starting, each request to the power manager is held
up to 90 seconds and the API gives up after 10 (`ReadTimeout` in the log, once a minute). Harmless but noisy; the
power manager should return at once when a wake is already under way.

**W10. Behind Vercel, "starting up" may show as a gateway error.** The console recognises the API's 503 `WAKING`
answer; while the database is mid-start the API can take longer than Vercel allows and the browser sees 502/504,
which are not recognised. (Not reproduced: needs the demo asleep.)

**W11. Nothing cleans up old rows.** Expired login codes, DigiLocker sign-in attempts and sessions, sync receipts,
published outbox rows and notifications are never deleted. DigiLocker access tokens of sessions that connect but
never import stay in the database (they are cleared only on import or on a 401).

**W12. No way to see portal-sync conflicts or school outreach lists.** Events the sync cannot place are "parked"
and alerted once, and Reach Radar produces per-school outreach lists, but neither has a console page.

**W13. Notifications reach only the app.** Alerts are polled once a minute while the app is open; SMS is stored
and not sent (documented). A student whose app is closed gets nothing.

### Low

- Visiting a page your role cannot use shows "Could not load this data" with a Retry button instead of a "no access"
  message (the API correctly refuses).
- Notification text mixes languages (Hindi sentence, English officer description).
- The 3-8 minute wake still depends on the first visitor; a scheduled morning warm-up would avoid it for demos.
- Hindi is missing from the Mitra screen and the server-settings sheet.
- Rate limits are counted per API instance, so the effective limit grows with instances.

## 4. Suggested order

1. **W1 and W2** together define whether a real student can get from sign-up to money; decide the payment source first.
2. **W3** (sessions) because it loses data.
3. **W6, W7, W4** are small and remove false or silent behaviour.
4. **W5, W8, W9, W10, W11, W12** next; **W13** needs a Firebase project and credentials.

## 5. Status after the fix pass (2026-10-03)

The decision behind it: the prototype keeps the **test DigiLocker** and the other test government services
(`DIGILOCKER_MODE=mock`); nothing here needs a real DigiLocker account. Every fix has a test
(`tests/integration/test_workflow_fixes.py`, `tests/unit/test_power_manager.py`, `apps/mobile/test/outbox_test.dart`).

| | Finding | Status | What changed |
|---|---|---|---|
| W1 | New DigiLocker student cannot be verified | Fixed | The test DigiLocker returns the Aadhaar reference and APAAR ID; sign-up stores them; verification then confirms identity and ST status without manual review. One identity, one record (a second sign-up is refused, 409). The test sign-in page lists test people. |
| W2 | Nothing pays after sanction | Fixed | The worker sends scheduled instalments of ScholarSetu applications to the (test) PFMS and records the result in the ledger. Chosen over an officer "release" button: it needs no extra step and PFMS reports the outcome. |
| W3 | 15-minute sessions, wiped phone | Fixed | Rotating refresh tokens (30 days idle) on the app and the console; a session ended by the server keeps unsent work; a 401 is never a permanent refusal. |
| W4 | Bank check does not gate | Fixed | Sanction is refused (409, with fix steps) while the check fails, and 503 while it cannot run. |
| W5 | Guardians and helpers cannot exist | **Open** | The sign-up endpoint accepts a role but the app has no choice and nothing links a guardian to a household. |
| W6 | Passports claim test data as UIDAI | Fixed | Sources read "(test)"; `test_data` is in the signed payload, the passport response and the offline verifier. |
| W7 | Gemini model name | Fixed in code | `deploy.sh` and `.env.example` use `gemini-3.8-flash`. The new key still has to be stored as a secret version (yours to do). |
| W8 | "More information" unanswerable | Fixed | `POST /v1/review/cases/{id}/respond`, a Reply button in the app, the answer shown to the officer. |
| W9 | Repeat wake requests time out | Fixed | The power manager answers at once when a wake is already under way. |
| W10 | 502/504 not treated as waking | Fixed | The console treats them like 503 WAKING; the app's error text does too. |
| W11 | Nothing cleans up | Fixed | `app/privacy/retention.py`, run by the worker every six hours; schedule in ARCHITECTURE §19 row 53. |
| W12 | No page for parked sync events / outreach | Fixed | Console "Portal sync" (sync now, parked statuses, mark handled) and "Outreach" (a school's unreached students). |
| W13 | Notifications only in the app | **Open** | Needs a push/SMS provider and credentials. |
| Low | No-access page | Fixed | Pages a role cannot use say so. |
| Low | Hindi missing in Mitra screen and server sheet | Fixed | |
| Low | Mixed-language notification text; per-instance rate limits; morning warm-up | Open | The officer's own description stays in the language they wrote it in. |
