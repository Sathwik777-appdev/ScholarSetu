# ScholarSetu — Build Plan

> The original build plan, kept for history. For what the prototype does today see the README and
> ARCHITECTURE.md §19 (Prototype Deviations).

## Phase 1: Project Foundation & Infrastructure

### 1.1 Root Project Setup
- Git init, .gitignore, README.md, LICENSE
- Docker Compose with all infrastructure services
- Root Makefile for common commands

### 1.2 Database & Core Models
- PostgreSQL schema with all entities from §7
- SQLAlchemy models (student, household, application, ledger_event, attestation, etc.)
- Alembic migrations
- Seed data scripts

### 1.3 FastAPI Modular Monolith Skeleton
- All 10 service modules as Python packages
- Shared kernel (events, types, errors, config)
- API Gateway with auth middleware
- Health checks, OpenAPI docs

### 1.4 Event Bus & Messaging
- NATS JetStream configuration
- Event publisher/subscriber base classes
- Event schemas (JSON Schema)

### 1.5 Mock External Services
- NSP, SFMP, NOS mock portals
- DigiLocker, UIDAI, AISHE, UDISE+, APAAR, e-District, UGC-NTA mocks
- PFMS/bank mock
- Synthetic data generator (Indian names, tribal data)

## Phase 2: Core Services Implementation

### 2.1 Scholarship Ledger (Event Sourcing + CQRS)
- Append-only event store with hash chain
- Read model projections (student_dashboard, family, money, SLA)
- Timeline API

### 2.2 Scheme Adapter Layer
- Base adapter interface
- NSP adapter with state mapping
- SFMP adapter with state mapping
- NOS adapter with state mapping
- Canonical lifecycle state machine

### 2.3 Verification Mesh
- Verifier plugin interface
- DigiLocker, UIDAI, AISHE, UDISE+, APAAR, e-District, UGC-NTA plugins
- Confidence scoring
- Manual review queue

### 2.4 Identity Resolver
- Name normalization pipeline
- Transliteration (Indic scripts → Roman)
- Phonetic key generation
- Token alignment & similarity scoring
- Corroboration logic
- Explanation generator

### 2.5 Attestation Service (Scholarship Passport)
- Attestation creation with Ed25519 signing
- Validity policy engine
- Reuse logic across schemes
- Export format

## Phase 3: Business Logic Services

### 3.1 Eligibility & Pathway Engine
- Decision tables (rules-as-code) for all 5 schemes
- One-scheme-at-a-time checker
- Transition detection & nudge triggers
- Pre-filled application generation

### 3.2 DBT Guardian
- Pre-sanction health checks
- Failure code mapping to plain-language
- Retry workflow
- Bank/Aadhaar seeding verification

### 3.3 Consent Manager
- DEPA-style consent artefacts
- Purpose-bound data access
- Revocation support

### 3.4 Document Wallet
- DigiLocker integration
- Local document management
- Compression & upload

### 3.5 Nudge & Notification Engine
- Event-driven notifications
- Multi-channel delivery (push, SMS, JAGO)
- Template management with i18n
- SLA escalation chains

## Phase 4: JAGO & Reach Radar

### 4.1 JAGO Scholarship Skill
- Tool server with all 7 tools
- RAG on scheme guidelines
- Grounding guardrails
- Hindi voice support
- Template-based money-safe responses

### 4.2 Reach Radar
- PPRL with Bloom filter encoding
- Coverage gap computation
- District/block heatmap data
- Outreach list generation

## Phase 5: Frontend Applications

### 5.1 Officer/Ministry Console (React)
- Review queue with explanations
- Coverage heatmaps (MapLibre)
- Analytics dashboards (ECharts)
- SLA monitoring

### 5.2 Flutter Mobile App
- Offline-first with Drift + SQLCipher
- Family mode
- Mitra (assisted) mode
- All 7 screens from §6.1

## Phase 6: Workflows & Integration

### 6.1 Temporal Workflows
- Verification workflow
- SLA monitoring workflow
- DBT retry workflow
- Deficiency resolution workflow

### 6.2 Integration Testing
- Contract tests against mocks
- End-to-end flow tests
- Identity matching evaluation suite
