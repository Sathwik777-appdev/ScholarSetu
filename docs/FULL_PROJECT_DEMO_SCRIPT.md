# ScholarSetu — Full Project Master Demo & Voiceover Script
## (Complete End-to-End: Mobile APK + Web Console + Cloud Architecture)

This is the **definitive 5-minute full project demonstration script** for **ScholarSetu**. It covers the complete ecosystem: the **Student Mobile APK**, the **Family & Mitra Assist Modes**, the **District Officer & Ministry Web Consoles**, the **Fuzzy Identity Resolver**, the **Immutable Hash-Chain Ledger**, and **Privacy-Preserving Reach Radar**.

---

## 📋 Master Recording Setup Checklist

### Screen Setup (Split Screen or Dual Window)
* **Left Screen (50%) — Mobile App (APK)**:
  * Android Phone mirrored via `scrcpy` (or Emulator) running `app-release.apk`.
  * One-tap demo accounts visible on login screen.
* **Right Screen (50%) — Web Browser (ScholarSetu Console)**:
  * **Tab 1**: [ScholarSetu Console](https://console-khaki-two.vercel.app)
  * **Tab 2**: [Live Swagger API Docs](https://scholarsetu-api-906769842576.asia-south1.run.app/docs)

### Master Credentials
| Persona | Role | Phone | OTP | Platform |
|---|---|---|---|---|
| **Sunita Hansda** | Student (Post-Matric) | `9876543210` | `123456` | Mobile APK |
| **Rahul Hansda** | Brother (Pre-Matric) | `9876543211` | `123456` | Mobile APK |
| **Babulal Hansda** | Father (Family Mode) | `9876543212` | `123456` | Mobile APK |
| **Kavita Tudu** | Mitra Helper (Warden) | `9876543220` | `123456` | Mobile APK |
| **District Officer** | DWO (Dumka, Jharkhand) | `9876543230` | `123456` | Web Console |
| **Ministry Official**| MoTA National Admin | `9876543240` | `123456` | Web Console |

---

## ⏱️ Master Timeline & Visual Action Plan

```
Total Video Time : 5 minutes 00 seconds
Pacing           : ~135 words/minute (deliberate, articulate, executive)
Structure        : APK (0:00–2:30) ➔ Web Console (2:30–4:25) ➔ Architecture & Vision (4:25–5:00)
```

---

### [0:00 – 0:35] Act 1: The Problem & The Glass Setu (Bridge)

#### 🖥️ What to Show
* Show the mobile app launch on the Android screen alongside the web console.
* Showcase the 3D Setu (bridge) landing art on the mobile login screen.

#### 🎙️ Spoken Voiceover
> *"Every academic year, thousands of Scheduled Tribe students disappear from the scholarship pipeline—not because they lack eligibility, but because of rigid administrative friction. Minor surname spelling variations across certificates, dormant bank accounts that fail Direct Benefit Transfer, and complete lack of internet connectivity in remote tribal hamlets result in unfair exclusions.*
>
> *This is **ScholarSetu**—a unified, offline-first digital public infrastructure built for the Ministry of Tribal Affairs. It links students, welfare officers, and national administrators through an intelligent verification mesh, proactive payment health checks, and a tamper-evident audit ledger.*
>
> *Let's begin with the student's journey on the ScholarSetu mobile app."*

---

### [0:35 – 1:15] Act 2: Mobile APK — Student Home & Scholarship Pathway

#### 🖥️ What to Show (Mobile APK)
1. Tap **Sunita Hansda (Student)** → Sign in with demo OTP `123456`.
2. On the **Home Tab**:
   * Show the personalized greeting: *"Hello, Sunita"*.
   * View the active **Post-Matric Application Card**: show stage status (*District Verification*).
   * Tap into the card to show the transparent milestone timeline.
3. Scroll to **"Your Scholarship Path"**:
   * Show the 5-rung ladder: Pre-Matric ➔ Post-Matric ➔ Top Class ➔ National Overseas ➔ Fellowship.

#### 🎙️ Spoken Voiceover
> *"Signing in as Sunita Hansda from Dumka, Jharkhand. The student mobile app eliminates the traditional black box.*
>
> *Right on her home screen, Sunita tracks her Post-Matric application through every milestone—from college nod to district approval. But ScholarSetu goes further: our **Scholarship Pathway Engine** transforms scholarships from isolated annual hurdles into a continuous academic ladder.*
>
> *From Pre-Matric to PhD fellowships, the moment an academic milestone or NET/JRF result is verified, the engine prepares pre-filled drafts for the next scheme automatically, preventing dropouts between school and higher education."*

---

### [1:15 – 1:50] Act 3: Mobile APK — Passport & Native DigiLocker Import

#### 🖥️ What to Show (Mobile APK)
1. Tap the **Passport** tab in the bottom bar.
2. Show verified credential badges (UIDAI Identity, e-District Income).
3. Tap **"Get from DigiLocker"**.
4. The test DigiLocker OAuth 2.0 PKCE consent screen opens in the browser.
5. Authorize and select the Caste Certificate → Tap Import.
6. The document lands in Sunita's encrypted wallet labeled with cryptographic provenance: **"DigiLocker (test)"**.

#### 🎙️ Spoken Voiceover
> *"Under the **Passport Tab**, students maintain a decentralized digital wallet of verified credentials. No more paying cyber cafés to scan paperwork.*
>
> *With native **DigiLocker partner integration**, Sunita connects via PKCE OAuth 2.0, authorizes access, and imports her officially issued caste certificate straight into her phone. Every document is stamped with cryptographic provenance, ensuring institutions and welfare officers can trust its authenticity instantly without demanding paper physicals."*

---

### [1:50 – 2:30] Act 4: Mobile APK — DBT Guardian, JAGO AI & Offline Sync

#### 🖥️ What to Show (Mobile APK)
1. Tap the **Money** tab:
   * Point out the **DBT Guardian Alert**: *"Aadhaar Not Seeded in Bank"*.
   * Tap the warning to reveal the plain-language Hindi guidance on visiting the bank branch to activate NPCI mapping *before* funds are released.
2. Tap the **JAGO AI** tab:
   * Type or tap: *"Post matric ki income limit kya hai?"*
   * Show JAGO quoting the exact clause (₹2,50,000/yr) with official MoTA guideline citation.
3. **Demonstrate Offline Resilience**:
   * Turn on **Airplane Mode** on the phone.
   * Point out the top banner: *"Saved copy. Last updated [time] — Offline Mode"*.
   * Tap the **Sync icon** in the top-right header to display the **Sync Screen**:
     * Show the **SQLCipher 256-bit encrypted database**.
     * Show the **Persistent Idempotent Outbox**.
   * Turn **Airplane Mode OFF** → Watch the sync indicator resolve in seconds.

#### 🎙️ Spoken Voiceover
> *"The number one cause of scholarship failure is DBT payment rejection—funds are sanctioned, but the bank account isn't seeded with NPCI. ScholarSetu's **DBT Guardian** runs proactive pre-disbursement health checks, alerting Sunita with clear Hindi instructions before payment initiation.*
>
> *For questions, **JAGO**, our localized RAG AI, provides instant answers grounded directly in official government gazettes via pgvector embeddings—citing clauses without hallucinating.*
>
> *And in connectivity shadows, ScholarSetu operates **offline-first**. All local data is encrypted with SQLCipher. Submissions are safely queued in an idempotent outbox and sync automatically the moment network coverage returns."*

---

### [2:30 – 3:20] Act 5: Web Console — DWO Dashboard & Fuzzy Identity Resolver

#### 🖥️ What to Show (Web Console)
1. Switch to the **Web Console** (`https://console-khaki-two.vercel.app`).
2. Sign in as **District Welfare Officer (9876543230)**.
3. Show the **Dashboard**: 3D interactive bars rendering application volume by stage, credited funds, and SLA alerts.
4. Navigate to the **Review Queue** → Open Sunita Hansda's case.
5. Highlight the **Fuzzy Identity Resolver**:
   * Aadhaar shows *"Sunita Hansda"*, but State Certificate has *"Sunita Hansdah"*.
   * Point out the 89% match score and the explanation highlighting the cultural dialect 'h'.
   * Enter note: *"Spelling verified by DWO"* ➔ Click **Approve**.
   * Show the toast: *"Recorded in ledger (Event ID: evt_...)"*.

#### 🎙️ Spoken Voiceover
> *"Now let's switch to the **District Welfare Officer's Web Console**.*
>
> *The officer dashboard provides instant visibility across all applications in the jurisdiction, backed by real-time SLA breach trackers. In the **Review Queue**, we see why Sunita’s application was paused: her caste certificate spelled her surname as 'Hansdah' with a trailing 'h'.*
>
> *In traditional portals, this causes immediate automated rejection. ScholarSetu's **Fuzzy Identity Resolver** understands tribal phonetics and dialect variations. It scores the match at 89%, corroborates demographic records from e-District, and routes it to the officer with evidence. With one click, the officer approves the correction—humane, intelligent governance in action."*

---

### [3:20 – 4:05] Act 6: Web Console — Application Timeline & Immutable Hash-Chain

#### 🖥️ What to Show (Web Console)
1. Open Sunita's **Application Detail Page**.
2. Scroll through the chronological audit timeline: every status change, consent token, and approval is recorded.
3. Point out the **Ledger Integrity Badge**:
   * *"Hash chain verified just now: 14 events, none altered, removed or reordered."*
4. Explain tamper-evidence: demonstrate that every transaction links to the previous event's SHA-256 hash.
5. Switch to **DBT Monitor**:
   * Show the payment pipeline: Sanctioned ➔ NPCI Mapper ➔ Bank Credits, with automated exponential backoff retries for transient banking failures.

#### 🎙️ Spoken Voiceover
> *"The moment the officer approves the review, the decision is committed to our **immutable, append-only ledger**.*
>
> *Every state transition, officer remark, and payment attempt forms a cryptographic hash chain. Right here on the application detail view, the system continuously verifies the hash chain. If an insider or bad actor modifies a single field in the underlying SQL database, the chain breaks instantly, creating a mathematically provable, non-repudiable audit trail.*
>
> *In the **DBT Monitor**, welfare officers can track payment pipelines in real time, with automated Temporal workflow retries for transient banking failures."*

---

### [4:05 – 4:35] Act 7: Web Console — Reach Radar (Privacy-Preserving Record Linkage)

#### 🖥️ What to Show (Web Console)
1. In the Web Console, navigate to **Reach Radar / Coverage Map**.
2. Switch between **"By District"** and **"By Block"**.
3. Point out the interactive 3D bars showing saturation percentages across Dumka, Ranchi, and Khunti.
4. Highlight the privacy banner:
   * *"Linked by hashed APAAR ID and Bloom-filter Cryptographic Long-term Keys (CLK) — No raw student identities or names exchanged."*
5. Show how underserved tribal pockets are pinpointed for targeted doorstep mobilization by Mitra volunteers.

#### 🎙️ Spoken Voiceover
> *"At the state and national level, the Ministry uses **Reach Radar**.*
>
> *How do we find eligible tribal children who haven't applied without violating data privacy? Reach Radar employs **Privacy-Preserving Record Linkage (PPRL)**. By cross-referencing UDISE+ school rosters against scholarship registers using Cryptographic Long-term Keys and Bloom-filter encodings, we identify saturation gaps without ever exposing raw student identities.*
>
> *Officers can drill down from state to block level, pinpointing underserved tribal clusters to dispatch Mitra field workers for doorstep enrollment."*

---

### [4:35 – 5:00] Act 8: Cloud Architecture & Closing Vision

#### 🖥️ What to Show
* Show the live system running in Google Cloud: Cloud Run (`scholarsetu-api`), Cloud SQL with pgvector, Secret Manager, NATS JetStream, and Temporal workflows on the backend VM.
* Bring the Mobile APK and the Web Console side-by-side for the final shot.

#### 🎙️ Spoken Voiceover
> *"ScholarSetu is fully production-ready, deployed live on Google Cloud with auto-scaling Cloud Run microservices, Cloud SQL with pgvector, NATS JetStream event streaming, and Temporal durable orchestration.*
>
> *By bridging the gap between student realities, offline constraints, and administrative integrity, ScholarSetu delivers on one core national mission:*
>
> ***Verify once, reuse everywhere, and never lose a tribal student between schemes, systems, or bank accounts.** Thank you."*

---

## 💡 Quick Reference: Keyboard & Screen Cues

| Section | Time | Screen Active | Key Action |
|---|---|---|---|
| **Intro** | `0:00 - 0:35` | Side-by-Side | Show 3D Setu Bridge & Web Console hero |
| **APK Home & Pathway** | `0:35 - 1:15` | Mobile APK | Login Sunita ➔ Stage tracker ➔ 5-rung Pathway ladder |
| **DigiLocker Import** | `1:15 - 1:50` | Mobile APK | Passport tab ➔ "Get from DigiLocker" ➔ Authorize ➔ Import badge |
| **DBT & Offline Sync** | `1:50 - 2:30` | Mobile APK | Money tab ➔ Airplane mode ➔ Sync screen (SQLCipher) ➔ Airplane mode off |
| **Officer Review Queue**| `2:30 - 3:20` | Web Console | DWO login ➔ Review queue ➔ Fuzzy Resolver (Hansda vs Hansdah) ➔ Approve |
| **Ledger Integrity** | `3:20 - 4:05` | Web Console | Application detail ➔ Verify hash chain badge ➔ DBT monitor |
| **Reach Radar** | `4:05 - 4:35` | Web Console | Reach Radar tab ➔ 3D saturation towers ➔ PPRL Bloom filter explanation |
| **Conclusion** | `4:35 - 5:00` | Side-by-Side | Cloud architecture & closing punchline |
