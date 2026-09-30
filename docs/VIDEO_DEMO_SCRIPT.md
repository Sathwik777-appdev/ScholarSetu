# ScholarSetu — 4 to 5 Minute Video Demo & Voiceover Script
## (Student Portal & Mobile APK Focused)

This script is structured to put the **Mobile App (APK) Student Portal** front and center, walking through all student-facing features, followed by a crisp demonstration of the Web Console to prove the end-to-end loop.

---

## 📋 Pre-Recording Setup Checklist

### 1. Screen Arrangement
* **Main Focus (70% of video)**: Android phone mirrored via `scrcpy` (or Android Studio Emulator) running `app-release.apk`.
* **Secondary Focus (30% of video)**: Web browser with:
  * **Tab 1**: [ScholarSetu Web Console](https://console-khaki-two.vercel.app)
  * **Tab 2**: [Live Swagger API Docs](https://scholarsetu-api-906769842576.asia-south1.run.app/docs)

### 2. Demo Credentials (One-Tap in APK)
| Persona | Role | Phone Number | OTP |
|---|---|---|---|
| **Sunita Hansda** | Student (Post-Matric Applicant) | `9876543210` | `123456` |
| **Babulal Hansda** | Father (Family Mode Shared Phone) | `9876543212` | `123456` |
| **Rahul Hansda** | Brother (Pre-Matric Recipient) | `9876543211` | `123456` |
| **District Officer** | District Welfare Officer (Dumka) | `9876543230` | `123456` |
| **Ministry Official** | MoTA Administrator | `9876543240` | `123456` |

---

## ⏱️ Video Timeline & Dialogue Breakdown

```
Total Duration : ~4:45 mins
Primary Device : Android APK (ScholarSetu Mobile)
Secondary      : Web Console (Officer & Ministry)
```

---

### [0:00 – 0:35] Part 1: Problem & Student App Introduction

#### 🖥️ What to Show (APK)
* Launch the APK on screen.
* Show the welcome screen with the 3D *Setu* (bridge) artwork and clean tribal design motifs.
* Highlight the one-tap demo personas at the bottom.

#### 🎙️ Voiceover Dialogue
> *"For millions of Scheduled Tribe students across India, applying for scholarships often means enduring arduous journeys to cyber cafés, rejected applications over minor spelling differences, and payments lost in dormant bank accounts.*
>
> *This is **ScholarSetu**—a modern, offline-first mobile portal and digital public infrastructure designed specifically for tribal students and their families.*
>
> *Today, we’ll demonstrate the complete student mobile experience right here on the Android app, along with our officer verification mesh."*

---

### [0:35 – 1:20] Part 2: Student Home, Application Tracker & Pathway

#### 🖥️ What to Show (APK)
1. Tap **Sunita Hansda (Student)** → Sign in with demo OTP `123456`.
2. Land on **Home Tab**:
   * Show the header: *"Hello, Sunita"* and scholarship received figure.
   * Point out the **Application Card**: Post-Matric Scholarship stage tracker (Submitted → Institute Verification → District Verification).
   * Tap into the application card: show the granular timeline and status history.
3. Scroll down to **"Things you need to do"**:
   * Show the pending notice regarding the certificate spelling discrepancy.
4. Scroll down to **"Your Scholarship Path"**:
   * Show the 5-rung ladder: Pre-Matric → Post-Matric → Top Class → National Overseas → Fellowship.

#### 🎙️ Voiceover Dialogue
> *"Signing in as Sunita Hansda from Dumka, Jharkhand. The student home dashboard is clean and transparent.*
>
> *Right at the top, Sunita sees exactly where her Post-Matric scholarship application stands in the verification lifecycle. There are no vague black boxes—every milestone from college nod to district approval is tracked in real time.*
>
> *Below her active application, ScholarSetu introduces the **Scholarship Pathway Engine**. Instead of treating scholarships as isolated yearly events, it guides students across their entire academic journey—from Pre-Matric all the way to PhD fellowships—pre-filling drafts as soon as academic milestones are verified."*

---

### [1:20 – 2:05] Part 3: Student Passport & "Get from DigiLocker"

#### 🖥️ What to Show (APK)
1. Tap the **Passport** tab in the bottom navigation bar.
2. Show Sunita's verified credentials:
   * Identity (UIDAI verified badge)
   * Caste Certificate (marked with source label)
   * Income Certificate
3. Tap the button: **"Get from DigiLocker"**.
4. The test DigiLocker OAuth 2.0 PKCE consent screen opens in the browser/in-app view.
5. Select the issued certificate → Authorize → Watch it import directly into Sunita's encrypted wallet with the badge **"DigiLocker (test)"**.

#### 🎙️ Voiceover Dialogue
> *"Next is the **Student Passport**—a decentralized, verifiable wallet of credentials. Students never need to upload photocopies or pay cyber café agents.*
>
> *With our native **DigiLocker partner integration**, Sunita taps 'Get from DigiLocker'. Using secure PKCE OAuth 2.0, the app connects to DigiLocker, allows her to select her officially issued documents, and imports them directly.*
>
> *Every document maintains strict provenance: clearly labeled with its originating source and cryptographic verification state."*

---

### [2:05 – 2:50] Part 4: Money Tab & Proactive DBT Guardian

#### 🖥️ What to Show (APK)
1. Tap the **Money** tab in the bottom navigation bar.
2. Show Sunita's DBT account overview:
   * Bank account details (masked for privacy).
   * **DBT Guardian Status Badge**: Point out the amber alert: **"Aadhaar Not Seeded in Bank"**.
3. Tap the alert to open the guidance modal:
   * Show the clear, actionable instructions in Hindi/English on how to visit the bank branch and link Aadhaar to the NPCI mapper.
4. Briefly switch to Rahul's card or profile to show a successful disbursement (₹4,000 Credited via PFMS).

#### 🎙️ Voiceover Dialogue
> *"Now let's examine the **Money Tab** and our proactive **DBT Guardian**.*
>
> *The number one cause of scholarship failure is payment rejection: funds are sanctioned, but the bank account isn't mapped to NPCI for Direct Benefit Transfer.*
>
> *ScholarSetu runs proactive pre-disbursement checks before funds ever leave the treasury. Sunita's app immediately warns her: her Aadhaar is not yet mapped to her bank account, giving her clear, step-by-step instructions in her local language on how to fix it before the sanction date. This prevents 99% of disbursement failures."*

---

### [2:50 – 3:35] Part 5: JAGO Multilingual AI & Offline Resilience

#### 🖥️ What to Show (APK)
1. Tap the **JAGO** tab in the navigation bar.
2. Show the multilingual chat interface.
3. Tap the prompt or type: *"Mera paisa kab aayega?"*
   * Show JAGO's response: It checks her actual ledger state, clarifies that verification is ongoing, and explains the timeline without hallucinating.
4. Ask: *"Post matric scholarship ki income limit kya hai?"*
   * Show JAGO quoting the exact official guideline clause (₹2,50,000/year) and citing the source document.
5. **Demonstrate Offline Mode**:
   * Pull down the Android status bar and enable **Airplane Mode**.
   * Show the amber top banner: *"Saved copy. Last updated [time]"*.
   * Tap the **Sync** icon in the top right to open the **Sync Screen**:
     * Show SQLCipher encryption confirmation.
     * Show the idempotent outbox queue ready to sync when back online.
   * Turn **Airplane Mode OFF** → Watch the banner resolve.

#### 🎙️ Voiceover Dialogue
> *"For instant support, Sunita turns to **JAGO**, our localized conversational AI.*
>
> *When asked about her disbursement, JAGO checks her live ledger state and gives an honest, accurate answer. When asked about scheme rules, JAGO queries our pgvector guideline index, citing official clauses rather than guessing.*
>
> *Furthermore, ScholarSetu is built strictly **offline-first**. In remote areas without cell reception, students can still view their saved records from an encrypted SQLCipher local database. Any upload or request is stored in an idempotent persistent outbox, syncing automatically the second a signal returns."*

---

### [3:35 – 4:15] Part 6: Family Mode & Officer Review Loop

#### 🖥️ What to Show (APK & Web Console)
1. On the APK, log out and tap **Babulal Hansda (Father: 9876543212)** → Sign in.
   * Show **Family Mode**: Both children (Sunita and Rahul) visible on one phone.
2. Switch to the **Web Console** (`console-khaki-two.vercel.app`):
   * Sign in as **District Welfare Officer (9876543230)**.
   * Open the **Review Queue** → Open Sunita Hansda's case.
   * Show the Fuzzy Name Resolver: Aadhaar has *"Sunita Hansda"*, certificate has *"Sunita Hansdah"*. The resolver scores it at 89% and flags the trailing 'h' as a dialect variance.
   * Enter remark *"Spelling verified by DWO"* and click **Approve**.
   * Show the toast: *"Recorded in ledger (Event ID: evt_...)"*.
3. Switch back to Sunita's APK and pull-to-refresh:
   * Show the stage tracker move forward to **Sanctioned / Approved**!

#### 🎙️ Voiceover Dialogue
> *"For parents sharing a single phone, **Family Mode** lets Babulal track all his children’s scholarships in one place.*
>
> *Now, notice why Sunita's application was flagged. On the **Officer Console**, the District Welfare Officer reviews her file. Sunita's caste certificate had a cultural dialect spelling—'Hansdah' with a trailing 'h'.*
>
> *Instead of an outright automated rejection, our **Fuzzy Identity Resolver** scored the match and queued it for human review. The officer approves the verification with one click, immediately committing the action to our immutable cryptographic hash-chain ledger.*
>
> *Returning to the APK and refreshing, Sunita's phone reflects the approved status in real time."*

---

### [4:15 – 4:45] Part 7: Reach Radar & Conclusion

#### 🖥️ What to Show (Web Console)
1. On the Web Console, navigate to **Reach Radar**.
2. Show the geographic saturation map and district saturation metrics (Dumka, Ranchi, Khunti).
3. Point out how Privacy-Preserving Record Linkage identifies eligible students who haven't applied yet, without exposing their raw personal identities.
4. Show the Mobile APK and Web Console side-by-side for the closing screen.

#### 🎙️ Voiceover Dialogue
> *"At the macro level, the Ministry uses **Reach Radar** with Privacy-Preserving Record Linkage to find eligible students who have dropped out of school rosters, mobilizing Mitra field workers to their doorsteps.*
>
> *From the offline student mobile app to the cryptographic ledger and ministry radar, ScholarSetu delivers on a single core promise:*
>
> ***Verify once, reuse everywhere, and never lose a tribal student between schemes, systems, or bank accounts.** Thank you."*

---

## 🛠️ Recording Checklist & Hotkeys

* **Scrcpy command** (mirrors Android device with high bitrate):
  ```bash
  scrcpy --max-size 1920 --bit-rate 16M --stay-awake
  ```
* **Emulator**: Run with pixel density 420 dpi, resolution 1080x2400.
* **Console URL**: `https://console-khaki-two.vercel.app`
* **API Documentation**: `https://scholarsetu-api-906769842576.asia-south1.run.app/docs`
