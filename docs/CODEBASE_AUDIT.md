# ScholarSetu — Codebase Audit

**Scope:** backend (`services/core`), mocks, mobile app (`apps/mobile`), console (`apps/console`), deployment
(`deploy/gcp`, `scripts/cloud_power.sh`, the power manager) and the live Google Cloud project.
**State audited:** `main` at `a22d194`, and the live project `trisphere-4b121`, on 2026-10-01.

---

## 1. Summary

The core logic is in good shape: role checks, consent, review decisions, DBT retries, offline sync and the
hash-chained ledger hold up. The test suite passes (446 passed, 1 skipped).

The most serious problems are in two places:
- **Concurrency.** Two requests arriving at the same moment can break four rules that hold when requests come
  one at a time. All four were proven with probes against the real test database.
- **The power automation added on 2026-09-30.** It exposes a public "shut everything down" URL, puts the demo
  to sleep at 4:30 PM India time every day, and never wakes it again automatically. It also gave the API
  project-wide admin rights over Cloud SQL and every VM.

| Severity | Count | Main sources |
|---|---|---|
| Critical | 4 | power manager, OTP checking, demo SMS outbox, service-account rights |
| High | 5 | ledger and application races, sleep/wake design, VM exposure, missing officer and verification screens |
| Medium | 9 | SMS flooding, deficiency attachments, CI, dependencies, app signing, AI guard, data rights, scale |
| Low | 5 | console advisories, file permissions, exit crash, approval values, lint warnings |

**If you fix only five things, fix these:**
1. **A1:** make the power manager private and call it with an authenticated scheduler.
2. **A2:** count OTP guesses atomically, so parallel guesses can't bypass the limits.
3. **A3:** take the SMS outbox off the public internet, even in demo mode.
4. **A4:** move the power manager to its own service account and remove the admin roles from the API's account.
5. **A5:** re-check the application's state after taking the row lock.

### How this was checked

- **Automated:**
  - full test suite (446 passed, 1 skipped, against Postgres and NATS in Docker);
  - `ruff`, `flutter analyze` and `flutter test`;
  - console `eslint`, `tsc` and `npm audit`;
  - `pip-audit` on every requirements file.
- **Manual:** I read the authentication, ledger, sync, verification, DBT, consent, SMS, JAGO, wallet and
  DigiLocker code and the deployment scripts.
- **Probes:** four concurrency probes ran against the test database. Each interleaved two database sessions the
  way two simultaneous requests would. Results are quoted under each finding.
- **Live project (read-only):** I checked IAM bindings, Cloud Scheduler jobs, the power manager's logs, VM
  network settings, firewall rules and endpoint reachability. I changed nothing and did not call `/sleep`.

---

## 2. Critical

### A1. Anyone on the internet can shut down the database and VM
`deploy/gcp/power-manager/main.py`

- **What happens:**
  - `scholarsetu-power` is deployed with `allUsers` as invoker, and CORS allows every origin.
  - `GET /sleep` stops the VM and sets the Cloud SQL instance to NEVER.
  - A link preview, a web crawler or a stranger opening that URL takes the whole system offline.
  - `/wake` is open too, so anyone can also run up the bill.
- **Why it's public:** the Cloud Scheduler jobs call it with no OIDC token, so the service had to be public.
- **Fix:**
  - remove `allUsers`;
  - give the scheduler jobs an OIDC token from a dedicated service account;
  - accept POST only;
  - drop CORS from `/sleep`;
  - expose wake-up to the console only through the API (see A7).

### A2. Login codes can be brute-forced with parallel requests
`services/core/app/gateway/service.py` (`_check_challenge`)

- **What happens:** the guess counter is read, compared and then incremented, with no row lock.
  Simultaneous guesses all pass the "too many attempts" check.
- **Probe:** 40 parallel wrong guesses were all checked against the code; only 2 attempts were recorded. The
  limits are 5 per code and 10 per hour.
- **Impact:** with demo mode off, an attacker can guess a six-digit login code for any account, including
  officers and the Ministry.
- **Fix:**
  - lock the challenge row (`SELECT … FOR UPDATE`), or increment atomically
    (`UPDATE … SET attempts = attempts + 1 … RETURNING`) before comparing;
  - also add per-IP rate limiting on the OTP endpoints, for example with Cloud Armor.

### A3. The demo SMS outbox shows every login code to anyone
`services/core/app/channels/router.py` (`/v1/dev/sms-outbox`)

- **What happens:**
  - In demo mode the page needs no login and lists every SMS, including OTPs and phone numbers.
  - The live deployment runs in demo mode and allows public self-registration.
  - So anyone can register any phone number, or sign in as any user who registered for real, by reading their
    code from that page.
  - The page currently returns 500 only because the database is asleep.
- **Fix:**
  - require an officer token for the page;
  - or show only demo users' messages and mask everything else;
  - or turn self-registration off in demo mode.

### A4. The API's service account can delete the database and control every VM in the project
Live IAM for `scholarsetu-demo@trisphere-4b121.iam.gserviceaccount.com`

- **What happens:**
  - Someone gave the account project-wide `roles/cloudsql.admin` and `roles/compute.instanceAdmin.v1` so the
    power manager could use it.
  - The API on Cloud Run, the worker and the VM all run as this account.
  - Any code-execution bug in the API could delete or export the database, or take over every VM in the
    project, including the unrelated `accessiq` and `backend` services.
- **Drift:** `deploy.sh` doesn't grant these roles, so the scripts no longer describe the real setup.
- **Fix:**
  - give the power manager its own service account, with the narrowest roles that can start and stop one
    instance and patch one Cloud SQL instance;
  - remove both admin roles from `scholarsetu-demo`;
  - put the power manager's setup in `deploy.sh`.

---

## 3. High

### A5. A rejected application can still be sanctioned
`services/core/app/ledger/service.py` (`transition`, `sanction`), `ledger/router.py`

- **What happens:**
  - `transition()` validates the move against `app.canonical_state` as it was loaded at the start of the
    request.
  - `append_event` then takes the row lock, but the state is never re-read after it.
  - So two officers acting at the same moment can both pass the check.
- **Probe:** officer A rejected; officer B, who had loaded the application earlier, sanctioned.
  - The sanction was accepted.
  - The application ended SANCTIONED, with payments scheduled and a `Rejected → Sanctioned` history.
  - `verify-chain` still reports the chain as valid.
- **Same pattern elsewhere:**
  - `update_payment()` (payment state);
  - `respond_deficiency()` (`resolved_at`);
  - the sanction endpoint's own state and open-case checks.
- **What saves the money:** the unique constraint on (application, instalment) stops a double sanction from
  creating duplicate payments. The second request fails with an unhandled 500 instead.
- **Fix:**
  - lock and refresh the application, or use `populate_existing`, before validating;
  - lock the payment row in `update_payment` and the deficiency row in `respond_deficiency`;
  - return 409, not 500, on the constraint violation.

### A6. The same scholarship can be applied for twice at once
`ledger/router.py` (`create_application`), `eligibility/service.py`

- **What happens:** the "one scheme at a time" and duplicate checks run in application code, and no database
  constraint backs them.
- **Probe:** two interleaved submissions for the same student, scheme and year each passed the check, creating
  2 applications. This happens with a double tap, or with an online submit racing the offline outbox.
- **Fix:**
  - add a partial unique index on (student_id, scheme, academic_year) for non-final states;
  - turn the violation into the existing 409 response.

### A7. Sleep and wake don't work as intended, and the demo goes down every afternoon
`deploy/gcp/power-manager/main.py`, Cloud Scheduler, `apps/console/src/api/client.ts`

- **Problem 1: the nightly sleep runs in the afternoon.** The "night safety sleep" job is `30 16 * * *` in
  `Asia/Kolkata`, so it shuts everything down at **4:30 PM India time every day**. The logs show it firing at
  11:00 UTC today.
- **Problem 2: the idle sleep never fires.** The uptime check probes `/health/ready` every 5 minutes from
  several regions. The idle check counts those probes as traffic: it saw 34 requests on every run today.
- **Problem 3: nothing ever wakes it.**
  - The console only triggers a wake on a 503 or a network error.
  - While the database is asleep, the API returns **500** (an unhandled `DBAPIError`).
  - So opening the console shows "Internal error" and never wakes anything.
- **Problem 4: misleading console message.** The console tells officers that *every* 503 means "servers were
  in zero-cost sleep mode and are now waking up". The API also returns 503 when storage is unavailable or
  DigiLocker isn't configured.
- **Problem 5: false alerts.** While asleep, the uptime alert policy fires and sends emails every night.
- **Fix:**
  - **schedule:** move the night sleep to a real night time, such as `30 1 * * *` IST, or drop it;
  - **API:**
    - return 503 with `Retry-After` when the database is unreachable;
    - have the API itself ask the (private) power manager to wake, so the console needs no third-party URL;
  - **idle check:** exclude uptime-check traffic, for example by user agent;
  - **monitoring:** pause the uptime check during sleep;
  - **console:** show the "waking up" message only for that specific 503.

### A8. The backend VM now has a public IP, with SSH and RDP open to the internet
`scripts/cloud_power.sh remove-nat`, live network

- **What happens:**
  - On 2026-09-30, `remove-nat` deleted the Cloud NAT and router and gave the VM an ephemeral public IP.
  - The default firewall rules open SSH (22) and RDP (3389) to `0.0.0.0/0`, so the VM is now reachable from
    anywhere whenever it runs.
  - Private Google Access is off, so the VM depends on that public IP for everything.
- **Script problems:**
  - `remove-nat` ignores a failure to add the IP (`|| true`) and deletes the NAT anyway, which would leave the
    VM with no internet;
  - `deploy.sh vm` recreates the NAT, so the two scripts fight each other.
- **Docs:** ARCHITECTURE.md §19 row 38 still says "no public IP".
- **Fix:** either:
  - restore NAT (about ₹2,700 a month);
  - or keep the IP but restrict SSH to IAP (`35.235.240.0/20`), delete the RDP rule, and turn on Private
    Google Access.

  Make the scripts agree with whichever you choose.

### A9. The core workflows have no screens
Console and app compared against the API.

- **Console:** apart from login, it can only decide review cases. There's no screen to:
  - move an application to the next stage;
  - raise a deficiency;
  - sanction (with the rule checks and override reason);
  - start a DBT check or retry;
  - open a document a student attached.

  ARCHITECTURE.md §19 row 11 says officers can do this "from the console", which isn't true today.
- **Both apps:** nothing can start verification (`POST /v1/verify/claims`), the "verify once, reuse
  everywhere" core. Only `scripts/demo_smoke_test.py` calls it.
- **Fix:** see features F1 and F2.

---

## 4. Medium

### A10. Registration can be used to flood a user's phone with SMS
`gateway/service.py` (`RegistrationService.start`)

- **What happens:** for a number that's already registered, the "already registered" SMS skips the rate
  limiter.
- **Probe:** 25 requests sent 25 SMS to the same user.
- **Fix:** put this branch under the same per-phone limit as code requests.

### A11. Deficiency replies accept any document IDs, and officers can't open the documents
`ledger/router.py` (`respond_to_deficiency`)

- **What happens:** `document_ids` are stored in the ledger without checking that they exist or belong to the
  student, so a reply can reference another student's document.
- **Console:** it shows the IDs only as raw JSON, with no way to open the document.
- **Fix:**
  - validate that the IDs belong to the student;
  - link each one to `/v1/wallet/documents/{id}/content`.

### A12. CI on `main` is red
`.github/workflows/ci.yml`

- **Lint:** `ruff` fails on 14 whitespace errors in `deploy/gcp/power-manager/main.py`.
- **Backend tests:** `test_outbox_publishes_to_nats_once` fails when NATS is unreachable, and the CI job
  starts no NATS service.
- **Fix:** run `ruff --fix` and add a `nats` service with `-js` to the job.

### A13. Dependencies aren't pinned, and the power manager pins vulnerable versions
- **Unpinned core:** `services/core/requirements.txt` has no version pins, so every image build can pull
  different, possibly breaking, versions.
- **Vulnerable power manager:** it pins FastAPI 0.115.0 (Starlette 0.38.6, 9 published advisories) and
  `requests` 2.32.3 (1 advisory).
- **Fix:**
  - use a lock file (`uv pip compile` or `pip-compile`) for every Python image;
  - upgrade the power manager;
  - turn on Dependabot.

### A14. Release APKs are signed with the debug key
`apps/mobile/android/app/build.gradle`

- **What happens:** `signingConfig = signingConfigs.getByName("debug")`.
- **Impact:** the APK can't go on the Play Store, and anyone holding the default debug key could ship an
  "update".
- **Fix:** add a release keystore, kept outside the repo, and sign with it.

### A15. The AI phrasing guard misses swapped, dropped or negated facts
`jago_skill/service.py` (`_figures_preserved`)

- **What happens:** the guard only checks that the AI text adds no new numbers or IDs.
- **What it misses:**
  - dropped figures;
  - two amounts that both appear in the answer being swapped (credited vs failed);
  - meaning flips, such as "has been credited" becoming "has not been credited".
- **Fix:**
  - require every figure to survive;
  - check that status words stay with their figures;
  - always show the verified text next to the AI version.

### A16. Students can't see or revoke consent, and can't ask for their data or its deletion
- **No consent screen:** the app has none, though the API has `/me/consents` and revoke.
- **Revoking is partial:** it stops future data pulls, but attestations and wallet copies already made stay.
- **No data rights:** there's no export or erasure request, which the DPDP Act expects.
- **Fix:** see feature F3.

### A17. The payment-failure advice promises an action the app doesn't have
`dbt_guardian/service.py` (`GUIDANCE`)

- **What happens:** students are told "Tell us here once the bank confirms, and we will check again". The app
  has no DBT status screen and no retry button.
- **Fix:** see feature F4, or change the wording until the screen exists.

### A18. Dashboards scan every open application in the country on each request
`ledger/service.py` (`sla_monitor`), `ledger/router.py` (`analytics_overview`, `/analytics/sla`)

- **What happens:** every open application nationwide is loaded and filtered in Python, even for one
  district officer.
- **Indexes:** officer filters wrap the state and district columns in a normalising function, so plain indexes
  can't help.
- **Fix:**
  - compute breaches in SQL, scoped to the officer's area;
  - store normalised state and district keys in indexed columns.

---

## 5. Low

- **A19. Console advisories:**
  - React Router 6 has a published open-redirect issue; no user input reaches `navigate` today, but it should
    still be upgraded;
  - Vite and esbuild advisories affect the dev server only.
- **A20. Local `.env`:** it's mode 644 (`make_env.py` creates it with 600). `DIGILOCKER_CLIENT_ID` and
  `DIGILOCKER_CLIENT_SECRET` are empty, so "Get from DigiLocker" returns 503 in the local stack until they're
  set.
- **A21. Exit crash:** one test run crashed at interpreter exit in the ONNX runtime
  (`recursive_mutex lock failed`) after the tests finished. It's flaky, and a crash at exit can fail CI.
- **A22. Free-form approval values:** an officer approving a case without source evidence can enter any
  `claim_value`; there's no per-claim schema, such as `tribe` and `pvtg` for ST status.
- **A23. Lint warnings:** six `react-refresh/only-export-components` warnings in the console.

**Not verified:** whether the Gemini model name `gemini-3.8-flash` exists. If it doesn't, AI phrasing silently
falls back to the verified text every time. One test call with the key would settle it.

---

## 6. Improvements and features

Ordered by value for the judges and for real users.

- **F1. Officer workbench in the console:**
  - stage moves;
  - raising a deficiency;
  - sanction with a live rule check and the override reason;
  - DBT check and retry;
  - an attached-document viewer and the student's wallet.

  The API already exists, so this is mostly UI work, and it closes A9 and A11.
- **F2. "Verify my details" in the app:**
  - the student reviews which sources will be checked;
  - grants consent in one tap;
  - sees each claim's result with a plain reason.

  This is the core value proposition and has no screen today.
- **F3. Consent centre:**
  - list, revoke, and show what each consent unlocked;
  - a data-export and erasure request, which officers process with an audit trail.
- **F4. "My bank is fixed" button:** runs the DBT check and retry from the app, so the guidance text becomes
  true.
- **F5. Sleep and wake done safely:** the A1, A4 and A7 fixes, plus a "Wake demo" button for officers in the
  console.
- **F6. Abuse protection:**
  - per-IP limits on OTP endpoints (Cloud Armor or an in-app limiter);
  - CAPTCHA after repeated failures;
  - limits on registration starts.
- **F7. Supply chain:**
  - lock files and Dependabot;
  - `pip-audit` and `npm audit` in CI;
  - release signing for the APK, and a Play internal-testing track.
- **F8. Push notifications (FCM):** instead of polling every minute (§19 row 26).
- **F9. QR Scholarship Passport:** the signed attestations already exist; a printable QR is the remaining step
  (§19 row 37).
- **F10. Scale:** SQL-side analytics (A18), and paging on the review queue and sync.

---

## 7. What is solid

- **Roles:** they're read from the database on every request, and tokens are checked for type and expiry.
- **Review decisions:** they lock the case row and check jurisdiction.
- **DBT retry:** it locks and refreshes the payment, and PFMS references are unique per attempt.
- **Offline sync:** each receipt commits in the same transaction as its action, so a replay never applies
  twice.
- **Consent:** checks cover owner, expiry, revocation, requester and every data item.
- **Inbound SMS:** the gateway is authenticated, and replies go only to the owner or their guardian.
- **Wallet:** content type comes from the bytes, integrity is checked on read, and each read is audited.
- **DigiLocker:** PKCE, single-use state, and test documents that can never appear issuer-signed.
- **Mobile:** cleartext HTTP is blocked in release builds, and the local cache is SQLCipher-encrypted.

---

## 8. Status after the fixes (2026-10-01)

Code fixes are tested: `tests/integration/test_audit_fixes.py` turns each audit probe into a regression test.

| # | Status | What changed |
|---|---|---|
| A1 | **Pending: live IAM** | The power manager is rewritten: POST-only actions, no CORS, uptime probes ignored by the idle check, and the downtime alert paused while asleep. Making it private, giving it its own service account and authenticating the scheduler are live IAM changes, not yet applied. |
| A2 | Fixed | The OTP challenge row is locked before checking. With 40 parallel guesses, exactly 5 are counted and the rest are refused. |
| A3 | Fixed | The public outbox shows demo accounts only. The full outbox needs a Ministry login, and every read is audited. |
| A4 | **Pending: live IAM** | Remove `cloudsql.admin`, `compute.instanceAdmin.v1` and `monitoring.viewer` from `scholarsetu-demo`. |
| A5 | Fixed | Every state check runs after `LedgerService.lock()` (row lock and reload). Payment and deficiency rows are locked too. |
| A6 | Fixed | A partial unique index (migration 0007), and a constraint conflict now returns 409. |
| A7 | Partly fixed | **In code:** the API returns 503 `WAKING` with `Retry-After` and asks the power manager to wake; the console shows the waking message only for that 503. **Pending (live):** moving the night sleep to 01:30 IST. |
| A8 | **Pending: live firewall** | `deploy.sh vm` and `cloud_power.sh remove-nat` now create the IAP-only SSH rule and the public-SSH/RDP deny rule, and enable Private Google Access. `remove-nat` stops if adding the IP fails. The live project still needs those rules applied. |
| A9 | Fixed | Console workbench (stage moves, deficiency, sanction with rule check, documents, bank check). App "Verify my details" with consent. |
| A10 | Fixed | The "already registered" SMS follows the per-phone hourly limit. |
| A11 | Fixed | Attachments must be the student's own wallet documents, and officers can open them from the timeline. |
| A12 | Fixed | The power manager passes lint; CI starts NATS with JetStream and audits dependencies. |
| A13 | Fixed | Lock files for all three images, Dependabot, and a clean `pip-audit`. |
| A14 | Fixed in the build; key needed | Release builds use `android/key.properties` when present and otherwise warn that they are debug-signed. You create the upload key and keep it; see the README. |
| A15 | Fixed | AI text must keep every figure in order and add no negation. |
| A16 | Fixed | App: Privacy & consent screen (withdraw, download my data, request correction or erasure). Console: data requests page. |
| A17 | Fixed | The app's failed-payment screen re-checks the bank and resends. |
| A18 | Fixed | SLA and bottleneck queries are scoped in SQL, with expression indexes on the place keys (migration 0008). |
| A19 | Fixed | Vite 6 and React Router 7; `npm audit` finds 0 vulnerabilities. |
| A20 | Fixed | Local `.env` is mode 600 and has generated DigiLocker test-client values. |
| A21 | Fixed | The test run exits with pytest's own status before the ONNX runtime is torn down. |
| A22 | Fixed | Manually approved values are checked against the fields each claim type needs. |
| A23 | Fixed | No console lint warnings remain. |

Features: F1, F2, F3, F4, F6, F7 (except release signing) and F9 are built. F5 is done in code, and its live half depends
on A1 and A4. F8 (FCM push) still needs a Firebase project and credentials; F10 is covered by A18.
