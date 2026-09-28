# ScholarSetu — Logic Audit

**Scope:** backend (`services/core`), mobile app (`apps/mobile`), console (`apps/console`), deployment files.
**State audited:** `main` at `22fce62` plus the uncommitted working-tree changes on 2026-09-28.
**Date:** 2026-09-28

---

## 1. Summary

The core ledger, verification, consent and sync logic is mostly sound. It has five real logic bugs,
one of which can send money twice. The most serious problems, though, arrived in the six commits
after Phase 12 (`1b44f94` … `22fce62`) and in uncommitted changes. These undo the security fixes
S1 and S7 from the validation report, and they return invented data as if it were real.

| Severity | Count | Where most of them come from |
|---|---|---|
| Critical | 8 | 7 from post-Phase-12 demo/deploy changes; 1 core (double payment) |
| High | 9 | invented data, Gemini integration, core sanction/payment rules, Cloud Run design |
| Medium | 9 | portal sync robustness, registration data quality, mobile server switching |
| Low | 3 | analytics scoping, test coverage |

**If you fix only five things, fix these:**
1. **L1–L4:** revert the uncommitted auth changes.
2. **L5–L6:** limit the demo code to seeded demo users again.
3. **L7:** stop shipping the JWT secret and signing key in the image.
4. **L8:** lock the payment before calling PFMS.
5. **L9–L10:** remove every invented-data fallback.

### How this was checked

- **Code read:** every diff since Phase 12, and the core modules (ledger, payments, DBT retry, eligibility, verification, consent, sync, adapters, auth, registration), read line by line.
- **Probes:** every finding marked **[reproduced]** has a probe test in `tests/audit/test_audit_probes.py`, run against the current code. A probe **passes while the bug is present**. Run them with:
  ```bash
  RUN_AUDIT_PROBES=1 pytest tests/audit -v      # 19 passed = 19 bugs present
  ```
  They are skipped in normal runs and in CI.
- **Test suite:** on the current tree, `pytest` fails 3 tests: `test_otp_locks_after_five_wrong_attempts`, `test_demo_otp_only_for_demo_users_in_demo_mode` and `test_defaults_are_safe`. The test setup forces `DEMO_MODE=false`, so none of the new demo-mode paths are exercised by CI. That is why most of the findings below were not caught.
- **Not done:** the live Cloud Run service was **not** probed. Findings about it come from its Dockerfile and the committed configuration.

Status key: **C** = committed · **U** = uncommitted working-tree change · **Core** = present since the fix phases.

---

## 2. Critical

### L1. `demo-token-<phone>` logs in as anyone, including the Ministry — U · [reproduced]
`services/core/app/dependencies.py::_user_from_token`: with `DEMO_MODE` on, a bearer token of the form
`demo-token-9876543240` is accepted without any signature and resolves to the user with that phone.
`GET /v1/analytics/overview` with `Authorization: Bearer demo-token-9876543240` returns the All-India ministry view.
**Fix:** delete this branch. Offline demo sessions in the app must never be valid on a server.

### L2. Any invalid token becomes Sunita's session — U · [reproduced]
The same function returns the user with phone 9876543210 (Sunita) when a token is malformed, badly signed, expired, or names a deleted user.
`Authorization: Bearer not-a-jwt` reads Sunita's dashboard.
Combined with L26, any page on `*.vercel.app` can read her data from a visitor's browser.
**Fix:** remove every fallback; an invalid token is always 401.

### L3. Token expiry is not checked, and tokens last 30 days — U · [reproduced]
- `shared/security.py`: `verify_exp = not settings.DEMO_MODE`, and `exp`/`iat` are no longer required.
- `config.py`: `JWT_EXPIRE_MINUTES = 43200`.
- A token that expired 400 days ago still works.

**Fix:** restore the 15-minute expiry, and always verify it.

### L4. The configuration now fails open — U · [reproduced]
`config.py` defaults were changed:
- `DEMO_MODE = True`
- `OTP_TTL_MINUTES = 60`
- `OTP_MAX_ATTEMPTS = 10`

Any deployment that forgets to set `DEMO_MODE=false` gets L1–L3, L5, L6 and L9. This is what breaks `test_defaults_are_safe`.
**Fix:** restore the defaults (`False`, 5 minutes, 5 attempts). Turn demo mode on only in demo environments.

### L5. The demo code logs in every user, and unknown numbers become Sunita — C (`2c410f6`) · [reproduced]
`gateway/service.py`:
- `_demo_otp_allowed` now reduces to `otp == DEMO_OTP`. A real, non-demo Ministry account logs in with `123456`.
- `verify_login_otp` logs any unregistered number in as Sunita.
- `request_login_otp` issues OTP challenges and SMS for unregistered numbers, which also violates the "same answer, no SMS" rule.

**Fix:** restore `settings.DEMO_MODE and user.is_demo and otp == settings.DEMO_OTP`. The persona chips in the app can stay; they only need seeded demo users.

### L6. Registration without confirming the phone — C (`2c410f6`) · [reproduced]
`RegistrationService.complete` skips the OTP check when the code is `123456`. Anyone can register any
phone number that isn't theirs, which undoes Phase 10's "phone confirmed by OTP" requirement.
**Fix:** never bypass the registration challenge. For demos, read the code from `/v1/dev/sms-outbox`.

### L7. The live API's signing secret is in git and in the image — C (`dc9430e`)
- `services/core/Dockerfile.cloudrun` sets `JWT_SECRET=supersecret-scholarsetu-jwt-demo-key-32chars-minimum` as an image `ENV`.
- The image build runs `seed_demo.py` with `DEMO_MODE=true`, which generates the Ed25519 attestation **private key into the image** (`/app/secrets`).
- Anyone with the repository or the image can forge access tokens for the deployed API and sign attestations. This reverses S7 and C8.

**Fix:**
1. Rotate the secret.
2. Pass `JWT_SECRET` and the signing key at runtime (Secret Manager → Cloud Run secrets).
3. Remove both from the Dockerfile.

### L8. Two retry taps send the money twice; the ledger records one — Core · [reproduced]
`dbt_guardian/service.py::request_retry` reads the payment, runs the health check and **calls PFMS
`initiate-payment` before taking any lock**. The payment update comes afterwards.
Two concurrent retries (a double tap, or app plus SMS) produce:
- two PFMS transfers;
- one request committing, and the other deadlocking and rolling back.

The result is **one transfer PFMS made that the ledger doesn't know about**. Reproduced on four runs out of four:
`retry statuses [200, 'DBAPIError'] PFMS transfers 2 retries recorded 1`.
**Fix:**
1. Lock the payment row (`SELECT … FOR UPDATE`, or the application lock `append_event` already uses).
2. Re-check `state == FAILED` after taking the lock.
3. Record the retry as `SUBMITTING` and commit.
4. Call PFMS with an idempotency reference that PFMS deduplicates (e.g. `payment_id:attempt_no`).
5. Settle from the reply.

---

## 3. High

### L9. The API returns invented records as real ones — U · [reproduced]
All three of these are presented as verified data.
- **Wallet** (`wallet/service.py::get_wallet`): a student with no documents gets five invented "verified" documents: an Aadhaar card with number 6234 8901 4183, a PAN card, a passport, a caste certificate and a marksheet. **Any** student gets them: Rahul's wallet shows documents whose metadata says the holder is "Sunita Hansda".
- **Passport** (`attestation/service.py::get_passport`): a student with no attestations gets five `ACTIVE` attestations with Sunita's name and `signature: "mock-jws-signature-…"`. `/v1/attestations/att-ident-001/verify` returns 404.
- **Analytics** (`reach_radar/service.py`): when linkage fails (UDISE+ down) or there are no rows, coverage, DBT failures and transitions return fixed numbers (Pakur 39.8%, 218 APAAR matches, …) with status 200. With UDISE+ down the API should return 503. It returns invented Dumka blocks instead.

These break the project's first ground rule ("never hardcode a result that should come from data; never return fake success"). They would be exposed by a single judge question.
**Fix:** delete the fallbacks. Empty means empty; unavailable means 503. Put any demo content in `seed_demo.py` as real rows.

### L10. The app invents data too, and labels it "verified" — C (`c03732e`, `22fce62`) + U · code read
- `login_screen.dart::_enterOfflineDemo` writes an invented dashboard, passport and wallet into the encrypted cache, **for every persona**.
- `PassportTab` shows five invented ACTIVE attestations and five invented identity documents whenever the real lists are empty.
- The document sheet says "✓ Cryptographically Verified by Issuer (Ed25519 Signed)" for **every** document, including ones the student uploaded, which are not verified.
- JAGO's offline replies say "currently under Authority Verification … no action is required" whatever the real stage is. The catch-all names `APP-PM-2026-000002` for any user.
- Online replies without citations are labelled "Verified MoTA Ledger + Gemini AI".

**Fix:**
1. Remove the fallbacks and the pre-seeding.
2. Show the verification label only when `verified == true`.
3. Build offline JAGO answers from the cached fields only, and say they are the saved copy.

### L11. Gemini rewrites ledger answers without any check — C (`d3ff2f0`) · [reproduced]
`jago_skill/service.py::_synthesize_with_gemini` replaces JAGO's ledger-grounded text with the model's reply.
- **Amounts not checked:** when the model returns "₹99,999", the student sees ₹99,999. Nothing checks that amounts, dates or IDs survived, and the student's message goes into the prompt, so prompt injection works too.
- **API key in the logs:** the key is in the URL query string, and httpx logs every request URL at INFO. The probe captured `…:generateContent?key=SECRET-K…` in the log.
- **Consent:** the student's question and their records go to Google without consent (DPDP).
- **False comment:** the module docstring still says "no generation, so no amount … can be invented".

**Fix:**
1. Send the key in the `x-goog-api-key` header.
2. After generation, extract every ₹ figure, date and application ID, and fall back to the deterministic text on any mismatch.
3. Add a consent check.
4. Update the docstring and the §19 deviation.

### L12. A script that forges realistic government ID documents — untracked
`scripts/generate_demo_documents.py` and `demo_documents/` produce "ultra-realistic" Aadhaar, PAN
and passport images and a KYC dossier: a simulated national emblem, UIDAI/NSDL/MEA issuer text,
QR codes and a portrait. Replicas of government identity documents create legal exposure (misuse of the
State Emblem, forgery) even for a fictional person, and would undermine the project's credibility if shown.
Also check that `sunita_photo.jpg` is not a photo of a real person.
**Fix:**
1. Do not commit or show these.
2. Delete them.
3. If sample documents are needed, use plainly fake layouts stamped "SPECIMEN — NOT A GOVERNMENT DOCUMENT", with no emblem.

### L13. A failed instalment disappears once a later one is credited — Core · [reproduced]
The application's state follows whichever instalment changed last. If instalment 1 fails
(`PAYMENT_FAILED`) and instalment 2 is then credited, the application becomes `CREDITED`. As a result:
- the dashboard's next action no longer mentions the failure;
- the SLA watch stops;
- the stage tracker shows every step done;

…while ₹3,000 is still unpaid (`total_failed = 3000`).
**Fix:** derive the application state from all instalments (any FAILED → PAYMENT_FAILED; all CREDITED → CREDITED; otherwise PAYMENT_INITIATED/SANCTIONED).

### L14. The one-scheme rule is not enforced at sanction — Core · [reproduced]
Applying while holding another scholarship only adds the flag `MUST_SURRENDER:<id>`. Nothing reads it:
the officer can sanction NFST while Post-Matric is still `SANCTIONED`, and the student holds two scholarships.
**Fix:** at sanction, refuse (409) while a flagged holding is still active, or surrender it in the same transaction and record both events.

### L15. Sanction and transitions ignore verification, eligibility and scheme amounts — Core · [reproduced]
- With the ST-status claim still provisional and its review case open, the district officer can sanction.
- The sanctioned amount can be anything up to ₹99,99,999 per instalment; it is not checked against the scheme's amounts in `rules/*.json`.
- The same applies to moving an application to AUTHORITY_VERIFICATION.

**Fix:** before sanction require:
- no open review cases;
- an `ELIGIBLE` eligibility decision on the current rule version;
- instalments that sum to at most the rule's entitlement.

Allow an explicit, audited officer override with a reason.

### L16. OTP guessing is limited per code, not per number — Core · [reproduced]
Each new OTP request resets the attempt count, and there is no limit on requests per phone or per IP.
The probe made 20 wrong guesses and was never locked out; an automated attacker can keep going (and floods the victim with SMS).
**Fix:**
- limit OTP requests per phone and per IP (e.g. 5 per hour);
- count failures across challenges for the phone, with a lockout;
- limit Mitra session creation the same way.

### L17. The Cloud Run deployment can't keep data and can't run the product's workflows — C (`dc9430e`, `22fce62`) · code read
`Dockerfile.cloudrun` runs PostgreSQL **inside the API container**, initialised at build time:
- **Data loss:** every restart, redeploy or scale-down loses all data. With more than one instance, each has its own database, so a code sent on one instance fails on another, and an application created on one is missing on the others.
- **Missing services:** no mock government services, NATS or Temporal worker, and `OUTBOX_PUBLISHER_ENABLED=false`. So:
  - no notification is ever created;
  - DBT retries stay `SUBMITTED` forever;
  - the outbox table grows without limit;
  - every verification ends as source-unavailable.
- **Wallet files:** documents go to `LocalFileStore` in `/tmp`, which is lost the same way. It also uses blocking file I/O inside async handlers.

**Fix:**
1. Use Cloud SQL (with pgvector) and object storage (GCS via its S3 API).
2. Deploy the mocks, NATS and the worker, or say plainly that those features are off in this deployment.
3. Pin to one instance until then.

---

## 4. Medium

### L18. One bad portal record stops the sync for everyone — Core · [reproduced]
In `adapters/sync_service.py`, an unknown scheme value in one NSP record raises `ValueError` from
`SchemeType(...)`. That aborts `sync_all`, so every student after it is never synced, on every cycle.
**Fix:** catch per application and per student; park the record with the reason and continue.

### L19. Portal imports bypass rules and blur the audit trail — Core · code read
- **One-scheme and duplicate checks skipped:** imported applications don't run them. A ScholarSetu application and its NSP copy become two applications.
- **Unmarked inferred steps:** when a portal jumps stages, the intermediate ledger events are written as if the portal reported them. They carry the final `source_status` and no `inferred` flag.
- **Unknown instalments dropped:** instalments the portal reports that the ledger doesn't have are skipped silently.

**Fix:**
1. Run the one-scheme check and link by source reference.
2. Mark inferred steps as `inferred: true`.
3. Park unknown instalments.

### L20. The same person can register many times — Core · [reproduced]
Registration only checks that the phone is new. Two phones register two "Sunita Hansda, 12-04-2008, Dumka"
students, each able to hold a scholarship, so the one-scheme rule is bypassed.
**Fix:**
1. Flag likely duplicates at registration (name + date of birth + district, using the identity resolver).
2. Hold them for review.
3. Link identities when the Aadhaar reference is verified.

### L21. A lowercase district hides the application from every officer — Core · [reproduced]
State and district are free text and jurisdiction matching is exact. A student who types
"jharkhand" / "dumka " is invisible to the district **and** state officers, so no SLA reminder reaches anyone.
**Fix:** pick state and district from a list (LGD codes); normalise on the server and store codes, not names.

### L22. Switching servers in the app keeps the old server's data — C (`1b44f94`) + U · code read
`Services.updateApiUrl` changes only the URL. The cache, sync cursor, outbox and token from the old
server all carry over:
- the cursor skips the new server's events;
- queued actions go to the wrong server;
- old data is shown as the saved copy.

Separately, the uncommitted `main.dart` silently replaces any saved LAN or emulator URL with the Cloud Run URL at every start.
**Fix:**
1. On a server change, sign out and wipe the database.
2. Drop the auto-migration, or ask the user first.

### L23. The app no longer says when it is offline — C (`dc9430e`)
`OfflineBanner` no longer shows the "no connection" line (Phase 10 requirement "truthful offline banner").
Only the small "Saved copy" chip remains, and the offline demo's invented data (L10) is shown under that same chip, as if it had come from the server.
**Fix:** restore the banner.

### L24. The APK allows plain HTTP to any host — C (`1b44f94`)
`usesCleartextTraffic="true"` and `base-config cleartextTrafficPermitted="true"` let tokens and OTPs
travel unencrypted over any network.
**Fix:** allow cleartext only in a debug build flavour, or only for the specific development hosts.

### L25. A personal phone number and pre-filled codes ship in the app — C (`2c410f6`)
- The persona list and the registration form contain **8867494183** ("You"), which looks like a real person's number, now shipped in every APK.
- Registration is pre-filled with Sunita's details and the code `123456`.
- The login screen auto-fills the code after sending it.

The Phase 10 rule was that no screen pre-fills an OTP.
**Fix:**
1. Remove the personal number.
2. Keep persona chips for seeded demo users only.
3. Never pre-fill codes.

### L26. CORS trusts every `*.vercel.app` site — U
`main.py` adds `allow_origin_regex=r"https://.*\.vercel\.app"` with credentials. Anyone can deploy a
Vercel site. With L2, such a site can read Sunita's data from any visitor's browser.
The console already reaches the API through the Vercel rewrite in `apps/console/vercel.json`, which is same-origin, so it doesn't need this.
**Fix:** remove the regex; list the exact console origin.

---

## 5. Low

### L27. State officers see other states' analytics — Core · code read
`reach_radar/router.py` filters DBT hotspots, transitions and coverage only for district officers. A
state officer sees every state's aggregates, while `/analytics/bottlenecks` is scoped correctly.
**Fix:** filter by `officer_covers` in those three endpoints (coverage needs the state on each row).

### L28. Demo login creates OTP challenges for unknown numbers — C (`2c410f6`)
Every request for an unregistered number now inserts a challenge and an SMS row. Unbounded growth, and SMS noise once a real gateway is connected.
**Fix:** part of L5.

### L29. No tests cover demo mode, and 3 tests fail today
The test setup pins `DEMO_MODE=false`, so none of L1–L6 or L9 is caught.
**Fix:** after fixing L1–L6, add tests that run with demo mode on and prove the bypasses stay closed. Turn the matching probes into regression tests.

---

## 6. What is working

These were checked and found correct:
- consent enforcement (owner, requester, items, expiry, revocation);
- attestation reuse (ACTIVE and unexpired only; provisional never reused);
- eligibility facts (expired attestations ignored; missing facts give "needs …");
- the hash chain (covers every field);
- the sync outbox's exactly-once receipts;
- wallet upload idempotency;
- officer jurisdiction on applications and review cases;
- the Mitra scope checks;
- the SLA escalation chain.

---

## 7. Suggested order of work

| # | Work | Findings | Effort |
|---|---|---|---|
| 1 | Revert the uncommitted auth and config changes; restore the demo-OTP rule; re-require the registration code | L1–L6, L28 | S |
| 2 | Rotate the JWT secret; move secrets and the signing key out of the image | L7 | S |
| 3 | Delete every invented-data fallback (API and app); fix the "verified" labels | L9, L10, L23 | S |
| 4 | Remove the document-forgery script and outputs; remove the personal number and pre-filled codes | L12, L25 | S |
| 5 | Lock-then-call PFMS with an idempotent reference | L8 | S |
| 6 | Payment-state aggregation; the one-scheme rule and gates at sanction | L13–L15 | M |
| 7 | OTP and session rate limits | L16 | S |
| 8 | Gemini: key in a header, figure/ID check, consent; docstring | L11 | S |
| 9 | Cloud Run: Cloud SQL, object storage, worker/NATS/mocks or declared off | L17 | M |
| 10 | Portal sync robustness and audit marks; registration dedupe and LGD codes | L18–L21 | M |
| 11 | App server switching; cleartext only for debug; CORS allowlist; analytics scope | L22, L24, L26, L27 | S |
| 12 | Demo-mode tests; probes become regression tests | L29 | S |

Effort: **S** ≈ under half a day · **M** ≈ 1–2 days.
