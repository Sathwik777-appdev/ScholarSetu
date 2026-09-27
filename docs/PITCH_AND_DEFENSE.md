# ScholarSetu — Pitch and Answers to Likely Questions
**SIH 2026 · Problem Statement 26238 · Ministry of Tribal Affairs · Team ACE**

Every claim below is something the prototype does today, or is marked as future work. Numbers about
students or budgets are not quoted here because we have not sourced them; cite the Ministry's own
published figures if you use any.

---

## 1. Thirty-second pitch

> Tribal students lose scholarships between systems: a name spelt differently on two documents, the same
> certificate verified again every year, a Class 10 student who never learns the next scheme exists, money
> sent to a bank account that cannot receive it. **ScholarSetu** sits in front of the existing portals:
> it verifies a claim once and signs it so every later application can reuse it, explains name
> differences instead of rejecting them, checks the bank account before money is sent, and tells the
> student — or their family, or a helper — exactly what to do next.

---

## 2. How it compares

| Capability | Typical portal today | ScholarSetu prototype |
|---|---|---|
| Moving from Pre-Matric to Post-Matric | Student must find and apply again | The pathway engine computes the next scheme from verified facts and prepares a pre-filled draft (student still submits it) |
| Name variants (Hansda / Hansdah / हांसदा) | Exact match or manual rejection | Identity resolver: transliteration + phonetic comparison + date of birth / father's name / district must agree; otherwise an officer reviews it with the reason shown. Never auto-rejects |
| Repeated certificate checks | Upload and verify each year | Confirmed claims become Ed25519-signed attestations reused by later applications until they expire |
| Payment failures | Discovered after the transfer bounces | DBT Guardian checks Aadhaar seeding, account status and name match first, and explains the fix |
| Help | FAQ or helpline | JAGO answers from the student's own ledger records and the official guideline text, with citations; says so when it cannot answer |
| Students who never applied | Invisible | Reach Radar links school enrolment to scholarship records without sharing raw identities and shows coverage by district and block |
| One family phone | One login per student | Family mode: a guardian sees every child's applications and money (read-only) |

---

## 3. Questions judges are likely to ask

### Q1. NSP already exists. Why this?
ScholarSetu does not replace NSP, SFMP or the NOS portal. Adapters read their application statuses into
one canonical lifecycle, and ScholarSetu adds what the portals do not do: reusable verification, name
resolution with explanations, pre-payment bank checks, proactive next steps, and coverage analytics.
In the prototype the portals are mocks (`/nsp`, `/sfmp`, `/nos`); status codes we do not recognise are
parked for review, never guessed.

### Q2. How do you tolerate name variants without letting fraud through?
The resolver transliterates each name to Latin (Devanagari, Bengali, Odia and other Indic scripts),
compares each token phonetically, and treats corroboration as a gate: an automatic match needs a high name
score **and** agreeing date of birth, father's name or district. Different first names (siblings), a
different surname, or any conflicting field go to an officer. The officer sees the actual score and the
reason, e.g. that the certificate spells "Hansdah" with a trailing h. It is tested against a labelled set
of pairs (`tests/identity_matching_eval/`) and the judge-probe test for siblings.

### Q3. How does "verify once, reuse everywhere" work?
When a source confirms a claim (say, ST status from e-District), the platform issues an attestation signed
with Ed25519 as a compact JWS. The public key is published at `/v1/attestations/public-key`, so anyone
can verify a copy offline; `/v1/attestations/{id}/verify` gives the current status (revoked or expired
attestations fail). Later applications reuse active attestations instead of asking the student again.
A QR/printable passport is not built yet.

### Q4. What about the DPDP Act?
- **Consent:** verification and document pulls need a recorded, purpose-bound, time-limited consent
  that the student can revoke; without one the API returns 403.
- **Assisted mode:** a Mitra (warden, CSC operator) gets access only after the *student* reads out an
  SMS code, for one purpose and a limited time; every action is audit-logged.
- **Record linkage:** Reach Radar compares keyed Bloom-filter encodings and hashed APAAR IDs, not names;
  officers other than the student's own school see counts only.
- **Integrity:** every application's history is a SHA-256 hash chain; changing any stored field of any
  event is detected by `verify-chain`.
- **On the phone:** the app's local data is encrypted with SQLCipher; the key lives in the phone's
  secure storage; signing out wipes it.

### Q5. Why Flutter for the student app?
It gives one codebase for Android (and iOS later), a mature encrypted local database, and good behaviour
on low-end phones and intermittent networks. Officers use a separate web console. Students without a
smartphone can text `STATUS <application id>` from their registered number (SMS is simulated in the
prototype).

### Q6. How does DBT Guardian prevent failed payments?
Before money is sent it queries the NPCI mapper and PFMS mocks: is Aadhaar seeded to an account, is the
account active, does the account holder's name match? Failures come with plain-language steps in Hindi
and English. If a payment still fails, the student confirms the fix and a Temporal workflow follows the
retry until PFMS reports it credited or failed.

### Q7. Can JAGO make up amounts or promises?
No language model is in the loop. Intents are routed by rules, amounts and dates are read from the
ledger's payment records, and replies use fixed bilingual templates; a test checks that every rupee
figure JAGO says equals the ledger. Guideline answers quote the official documents with a citation, and
below a relevance threshold JAGO says it could not find the answer.

### Q8. How would states and portals connect?
Each portal gets an adapter with a state map (`adapters/<portal>/state_map.yaml`) that translates its
status codes into the canonical lifecycle. Events are published on NATS JetStream for any consumer; the
event format is a published JSON Schema (`contracts/events.schema.json`) checked by tests.

### Q9. What would the Ministry gain?
We have not measured savings. What the prototype demonstrates is the mechanism: fewer repeat
verifications (reused attestations), payment problems caught before transfer, SLA breaches escalated
automatically, and the unreached students made visible by district and block. A pilot would measure the
effect.

### Q10. What is needed for production?
Real integrations (DigiLocker partner access, UIDAI via an authorised agency, NPCI/PFMS, the portals'
APIs), an SMS gateway, Keycloak or the government SSO, a hardened Temporal cluster, verified scheme values
(`docs/RULE_VALUES_TO_VERIFY.md`), languages beyond Hindi and English, and a pilot to tune the identity
thresholds on real, anonymised data. See ARCHITECTURE.md §19 for every current shortcut.

---

## 4. Demo setup

| Window | What to show |
|---|---|
| Android emulator (Flutter app) | Family mode, registration state, offline banner and outbox, JAGO |
| Console, http://localhost:5173 | District officer: review queue and decision; ministry: dashboard, coverage |
| Terminal | `make smoke-test` — the eight scenes checked by content |

Scene-by-scene script: [demo-script.md](demo-script.md).
