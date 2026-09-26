# ScholarSetu — Judge Demo Script (≈7 minutes)

## Setup Before Demo
```bash
# Start all services
cd /path/to/scholarsetu
make dev   # or: docker-compose -f infra/docker-compose.yml up -d

# Verify all services are healthy
curl http://localhost:8000/health   # Core API
curl http://localhost:8100/health   # Mock services
# Open http://localhost:5173        # Officer console
```

---

## Persona
**Sunita Hansda** — Class 10 pass from Dumka district, Jharkhand (tribal district).  
Her younger brother **Rahul Hansda** is in Class 9 (Pre-Matric scholarship, already credited).  
Their father has one shared Android phone.  
Hostel warden helps students apply.

---

## Scene 1: Family Mode (0:00 – 0:45)

**Narration:** "Meet Sunita's father. One phone, two children, two different scholarships."

**Actions:**
1. Open the mobile app (or demo the API responses)
2. Show the family dashboard: `GET /v1/me/household`
   - Brother Rahul: Pre-Matric → **Credited** ✅ (₹7,000 received)
   - Sunita: No active application → "Eligible for Post-Matric" nudge visible
3. **Key talking point:** "One device, one parent, complete visibility across all children and all schemes."

---

## Scene 2: Pathway Nudge — Transition Detection (0:45 – 1:30)

**Narration:** "Sunita passed Class 10. The system knows."

**Actions:**
1. Show that Sunita's Class 10 marksheet appeared in DigiLocker (mock event)
2. The Pathway Engine detected the transition:
   ```
   GET /v1/me/pathway
   → current: Pre-Matric (completed)
   → next_eligible: Post-Matric
   → transition_trigger: "Class 10 result detected"
   → pre_filled_available: true
   ```
3. Show the pre-filled Post-Matric application:
   - ST attestation **reused from Pre-Matric** (valid lifetime) — no re-upload
   - Identity attestation **reused** — no re-verification
   - Only income (expired, needs renewal) and AISHE enrolment need verification
4. **Key talking point:** "Verify once, reuse everywhere. The Scholarship Passport eliminates repeated uploads."

---

## Scene 3: Verification Mesh + Identity Resolution (1:30 – 2:45)

**Narration:** "Now watch what happens with a real-world name mismatch."

**Actions:**
1. Submit the application → triggers Verification Mesh
2. Show the verification flow:
   ```
   POST /v1/verify/claims
   → ST_STATUS: REUSED (existing attestation, confidence 0.98)
   → IDENTITY: REUSED (existing attestation)
   → INCOME: Pulling from e-District mock...
   → HIGHER_ED: Verifying via AISHE mock...
   ```
3. **The identity mismatch moment:**
   - Aadhaar says: "Sunita Hansda"
   - School record says: "Sunita Hansdah"
   - e-District says: "सुनीता हांसदा"
4. Show the Identity Resolver output:
   ```json
   {
     "overall_score": 0.88,
     "decision": "PROVISIONAL",
     "explanation": "Surname differs by trailing 'h' (Hansda vs Hansdah). 
                     Devanagari transliteration matches. DOB and father's 
                     name match exactly. Score: 0.88 (provisional range).",
     "name_comparisons": [...]
   }
   ```
5. **Critical point:** "The application CONTINUES with a provisional flag. It is NOT blocked. This goes to an officer review queue with a clear explanation."
6. **Key talking point:** "Most systems would reject Sunita here. We understand Indian name variations."

---

## Scene 4: DBT Guardian (2:45 – 3:30)

**Narration:** "The scholarship is sanctioned. But will the money actually reach Sunita?"

**Actions:**
1. Show the pre-sanction DBT health check:
   ```
   POST /v1/dbt/health-check/{application_id}
   → aadhaar_seeded: false ❌
   → account_active: true ✅
   → name_match: 0.95 ✅
   ```
2. Show the plain-language message (in Hindi):
   ```
   "आपका आधार सरकारी भुगतान के लिए बैंक खाते से जुड़ा नहीं है। 
    अपना आधार कार्ड लेकर बैंक जाएं।"
   ```
3. With clear fix steps:
   - "Carry your Aadhaar card to your bank branch"
   - "Ask for NPCI/DBT Aadhaar seeding"
   - "This is different from Aadhaar linking"
4. **Key talking point:** "We catch payment problems BEFORE they happen, and tell students exactly what to do — in their language."

---

## Scene 5: JAGO Voice (3:30 – 4:30)

**Narration:** "Sunita asks in Hindi: 'Mera paisa kab aayega?'"

**Actions:**
1. Send message to JAGO:
   ```
   POST /v1/jago/chat
   {
     "message": "Mera paisa kab aayega?",
     "language": "hi",
     "channel": "voice"
   }
   ```
2. Show the grounded response (NOT hallucinated):
   ```
   "आपकी Post-Matric छात्रवृत्ति (APP-PM-2026-000812) स्वीकृत हो चुकी है। 
    भुगतान 3 दिन पहले भेजा गया है। लेकिन आपका आधार बैंक खाते से DBT 
    के लिए जुड़ा नहीं है। कृपया पहले बैंक जाकर आधार सीडिंग करवाएं।"
   ```
3. Show the tool calls made (transparent):
   - `get_payments(student_id)` → Sanctioned, PaymentInitiated 3 days ago
   - `get_pending_actions(student_id)` → Aadhaar seeding needed
4. **Key talking point:** "Every number and date comes from the database, not the AI. JAGO cannot hallucinate money amounts."

---

## Scene 6: Offline + SMS (4:30 – 5:15)

**Narration:** "What if there's no internet? What if there's no smartphone?"

**Actions:**
1. Show offline capability:
   - Switch to airplane mode (simulated)
   - Dashboard still shows all data (from local encrypted DB)
   - Queue an upload → it's saved to the outbox
   - Come back online → automatic sync
2. Show SMS fallback:
   ```
   SMS: STATUS APP-PM-2026-000812
   Reply: "Your Post-Matric application is SANCTIONED. Payment initiated. 
           Action needed: Aadhaar bank seeding. Visit bank with Aadhaar."
   ```
3. **Key talking point:** "We design for the student who has a feature phone, shared device, and intermittent connectivity."

---

## Scene 7: Officer Console (5:15 – 6:00)

**Narration:** "Now the officer's side."

**Actions:**
1. Open the Officer Console (http://localhost:5173)
2. **Review Queue:** Show the queue sorted by SLA risk
   - Sunita's case is there with the clear explanation
   - Side-by-side evidence view
   - One-click "Approve" → Sunita's timeline updates immediately
3. **Dashboard:** Show the ministry overview
   - Applications by scheme (bar chart)
   - Applications by state (pie chart)
   - SLA breaches highlighted
4. **Key talking point:** "Officers get explainable AI recommendations, not black boxes."

---

## Scene 8: Reach Radar (6:00 – 7:00)

**Narration:** "The hardest problem: finding the students who never applied."

**Actions:**
1. Open the Coverage Map page
2. Show the district-level heatmap:
   - Dumka district: 72% coverage
   - A nearby block: only 31% coverage (red)
3. Show the analysis:
   - "1,247 ST students enrolled in UDISE+ but not in any scholarship system"
   - "Done using privacy-preserving record linkage — no raw PII was shared"
4. Show the outreach list:
   - Sent only to the school headmaster (who already knows these students)
   - Contains count, not individual details
5. Show transition analysis:
   - "Class 10 → Post-Matric conversion: 64% in this block vs 82% state average"
6. **Closing pitch:**
   > "ScholarSetu doesn't just digitize forms. It verifies once and reuses everywhere. 
   > It understands Indian name variations. It catches payment failures before they happen. 
   > And it finds the students who fall through the cracks — without compromising their privacy. 
   > One bridge between the student and every scholarship system."

---

## Backup Demos (if judges ask)

### Mitra Mode
- Show OTP-based consent flow
- Time-boxed, scope-limited access
- Audit trail of all actions

### Attestation Export
- Show a signed attestation with Ed25519 signature
- Explain W3C Verifiable Credential path

### Rules-as-Code
- Open a decision table JSON
- Change an income limit
- Show the eligibility check uses the updated rule
- "No code change needed. Policy changes are configuration."

### Event Chain Verification
- Run hash chain verification on an application
- Show tamper detection capability
