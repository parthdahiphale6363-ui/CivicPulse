# 🏛️ CivicPulse: Next-Gen Municipal Intelligence & Civic Resolution Ecosystem

<div align="center">

![CivicPulse Banner](https://img.shields.io/badge/CivicPulse-Municipal%20Command%20Center-6366f1?style=for-the-badge&logo=civicrm&logoColor=white)

[![Python Version](https://img.shields.io/badge/Python-3.9%20%7C%203.10%20%7C%203.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Flask Framework](https://img.shields.io/badge/Flask-2.3+-000000?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Groq AI](https://img.shields.io/badge/Groq%20Cloud-Llama%203%20%7C%20Qwen%20%7C%20Whisper-F55036?style=flat-square&logo=speedtest&logoColor=white)](https://groq.com/)
[![Vector Database](https://img.shields.io/badge/Vector%20Store-PGVector%20%7C%20Supabase-3ECF8E?style=flat-square&logo=supabase&logoColor=white)](https://supabase.com/)
[![Embeddings](https://img.shields.io/badge/FastEmbed-ONNX%20%28No%20Torch%29-FF6F00?style=flat-square)](https://qdrant.github.io/fastembed/)
[![Database](https://img.shields.io/badge/Database-SQLite%20%7C%20PostgreSQL-336791?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Security](https://img.shields.io/badge/Security-CSRF%20%7C%20Rate%20Limited%20%7C%20RBAC-success?style=flat-square&logo=shield&logoColor=white)](#-security-privacy--reliability)
[![UI Engine](https://img.shields.io/badge/UI-3D%20Glassmorphism%20%26%20Vanilla%20CSS-blueviolet?style=flat-square)](https://developer.mozilla.org/en-US/docs/Web/CSS)

**CivicPulse** is an enterprise-grade municipal intelligence platform designed to bridge the chasm between everyday citizens and urban local bodies. By replacing obsolete grievance portals with **Verified Retrieval-Augmented Generation (RAG)**, **Multilingual Speech Intelligence**, **Computer Vision Verification**, and **Autonomous Ticket Triaging**, CivicPulse transforms city administration from *reactive firefighting* into *proactive, data-driven governance*.

[Key Features](#-core-platform-modules) • [RAG Knowledge Base & Retrieval](#-verified-rag-knowledge-base--retrieval-architecture) • [Data Schema & Storage](#-data-architecture-what-data-we-store) • [Technology Stack](#-technology-stack-deep-dive) • [Setup & Deployment](#-installation--setup-guide)

</div>

---

## 📑 Table of Contents
1. [🌟 Vision & Executive Summary](#-vision--executive-summary)
2. [🏗️ High-Level System Architecture](#️-high-level-system-architecture)
3. [🧠 Verified RAG Knowledge Base & Retrieval Architecture](#-verified-rag-knowledge-base--retrieval-architecture)
   - [Knowledge Base Composition (50+ Audited SOPs & Acts)](#1-knowledge-base-composition-50-audited-sops--acts)
   - [Zero-Hallucination Policy & Provenance Verification](#2-zero-hallucination-policy--provenance-verification)
   - [Hierarchical Chunking & Ingestion Engine (`rag/ingest.py`)](#3-hierarchical-chunking--ingestion-engine-ragingestpy)
   - [Dual-Engine Vector Retrieval (Direct SQL vs. LangChain)](#4-dual-engine-vector-retrieval-direct-sql-vs-langchain)
   - [Guardrails, Sanitization & Safe-Valve Memory Watcher](#5-guardrails-sanitization--safe-valve-memory-watcher)
4. [💾 Data Architecture: What Data We Store](#-data-architecture-what-data-we-store)
   - [Relational Matrix & Table Schemas](#1-relational-matrix--table-schemas)
   - [Vector Space & Embedding Storage](#2-vector-space--embedding-storage)
   - [Lifecycle Telemetry & Timeline Auditing](#3-lifecycle-telemetry--timeline-auditing)
5. [💻 Technology Stack Deep-Dive](#-technology-stack-deep-dive)
6. [🚀 Core Platform Modules](#-core-platform-modules)
   - [Voice-First AI Reporting Engine](#1-voice-first-ai-reporting-engine)
   - [AI Computer Vision Evidence Inspector](#2-ai-computer-vision-evidence-inspector)
   - [Semantic & Geodesic Deduplication](#3-semantic--geodesic-deduplication)
   - [CivicIQ City Assistant & RTI Generator](#4-civiciq-city-assistant--rti-generator)
   - [Municipal Admin Command Center](#5-municipal-admin-command-center)
   - [LivePulse City Dashboard & Gamification](#6-livepulse-city-dashboard--gamification)
7. [🛡️ Security, Privacy & Reliability](#-security-privacy--reliability)
8. [🔌 REST API Reference](#-rest-api-reference)
9. [⚙️ Installation & Setup Guide](#-installation--setup-guide)
10. [🌐 Deployment Strategies](#-deployment-strategies)

---

## 🌟 Vision & Executive Summary

Conventional civic grievance systems suffer from critical points of failure:
- **High Friction**: Citizens struggle with complex forms, bureaucratic terminology, and mandatory typed inputs in non-native languages.
- **Duplicate Explosion**: A single pothole on a major arterial road generates dozens of disjointed tickets across multiple departments.
- **Opaque Processing**: Grievances vanish into bureaucratic "black holes" without transparent escalation matrices or clear accountability.
- **AI Hallucinations in Civic Tech**: Generic chatbots frequently invent unrealistic repair deadlines (e.g. *"This will be fixed in 24 hours"*), wrong contact numbers, or fictitious departments.

**CivicPulse eliminates these bottlenecks** through a strictly grounded, multi-agent AI framework:
1. Citizens can speak naturally in **Hindi, Marathi, Hinglish, or English** to file fully structured complaints.
2. Reports are cross-referenced with **grounded municipal standard operating procedures (SOPs)** and legal statutes via **FastEmbed + PGVector**.
3. All AI suggestions and department routings are **grounded in verified city bylaws** with direct source citations and post-generation assertion sanitizers.
4. Municipal administrators receive auto-triaged tickets complete with **3-point tactical action plans**, viral outrage risk assessments, and workload heatmaps.

---

## 🏗️ High-Level System Architecture

```mermaid
flowchart TD
    subgraph Citizens ["Citizen Ingress Layer"]
        Voice["🎙️ Multilingual Voice Audio (WebRTC)"]
        Form["📝 Structured Grievance Web Form"]
        Vision["📸 Photographic / Video Evidence"]
    end

    subgraph IngestionAI ["Ingress Intelligence & Ingestion"]
        Whisper["Groq Whisper Large-v3\n(Audio Transcription)"]
        VisionLLM["LLaMA 3.2 Vision\n(Artifact & Decay Verification)"]
        Parser["LLM Structuring Engine\n(JSON Output & Priority Tagging)"]
        Dedupe["Geodesic & Embedding Deduplication\n(Proximity + Semantic Match)"]
    end

    subgraph Storage ["Unified Persistence Layer"]
        RelationalDB[("Relational Database\nSQLite / PostgreSQL\nUsers, Complaints, Timelines")]
        PGVectorDB[("PGVector / Supabase\nVector Store: civic_kb\n50+ Audited Municipal SOPs")]
    end

    subgraph RAGCore ["Verified RAG & Retrieval Engine"]
        Rewriter["Query Rewriter\n(Multilingual -> Standalone English)"]
        FastEmbed["FastEmbed ONNX\n(sentence-transformers/all-MiniLM-L6-v2)"]
        Retriever["Lightweight SQL Vector Search\n(<=> Cosine Distance <= 0.3)"]
        Sanitizer["Claim Sanitizer & Guardrails\n(Purges Invented SLAs & Fictitious Corp Names)"]
    end

    subgraph Delivery ["Civic Command & Citizen Delivery"]
        AdminDash["👑 Municipal Command Center\n(Triage, Action Plans, Dispatch, Workloads)"]
        CitizenPortal["📱 LivePulse & Community Portal\n(Timeline, Upvoting, Gamification)"]
        CivicIQBot["🤖 CivicIQ Assistant\n(RTI Generator, Legal Rights, City Health Scan)"]
    end

    Voice --> Whisper --> Parser
    Vision --> VisionLLM --> Parser
    Form --> Parser
    Parser --> Dedupe
    Dedupe --> RelationalDB

    RelationalDB -.-> Rewriter
    CivicIQBot -.-> Rewriter
    Rewriter --> FastEmbed --> Retriever
    PGVectorDB <--> Retriever
    Retriever --> Sanitizer

    Sanitizer --> AdminDash
    Sanitizer --> CivicIQBot
    RelationalDB --> AdminDash
    RelationalDB --> CitizenPortal
```

---

## 🧠 Verified RAG Knowledge Base & Retrieval Architecture

CivicPulse implements an industrial-grade **Retrieval-Augmented Generation (RAG)** pipeline designed to guarantee zero hallucinations in municipal governance.

```
📁 knowledge/
 ├── 📜 _PROVENANCE.md             # Complete source attribution audit trail
 ├── 📜 _REVIEW.md                 # Automated drop-log for unverified lines
 ├── 📁 _sources_cache/            # Frozen HTML/Markdown snapshots of live gov portals
 ├── 📁 rates/                     # Municipal scheduled rates & tax norms
 ├── 📘 dept_*.md                  # Department mandate & jurisdiction guides (7 files)
 ├── 📙 sop_*.md                   # Standard Operating Procedures for field crews (10 files)
 ├── 📗 playbook_*.md              # Tactical resolution workflows & triage logic (11 files)
 ├── ⚖️ legal_*.md                 # SWM Rules 2016, Plastic Ban, RTS Act, Pollution Acts (5 files)
 ├── 🆘 disaster_*.md              # Urban flooding, heatwave, structural fire safety (3 files)
 ├── 🏥 health_*.md                # Vector-borne diseases, water-borne outbreaks, animal control (3 files)
 ├── 🏗️ infra_*.md                 # Water networks, drainage, road pavement layers, SWM (4 files)
 ├── ⛅ seasonal_*.md              # Pre-monsoon desilting, summer drought management (2 files)
 ├── 📑 rti_guide.md               # Complete Right to Information manual (Central & MH)
 └── 🌲 env_*.md                   # Tree protection acts, CPCB AQI, water bodies (3 files)
```

### 1. Knowledge Base Composition (50+ Audited SOPs & Acts)
The knowledge repository under `knowledge/` contains over **50 structured Markdown manuals** categorized into specific administrative scopes:

| Category | Files / Scope | Primary Sources | Key Coverage |
|---|---|---|---|
| **Department Directives** | `dept_public_works.md`, `dept_water_sewerage.md`, `dept_electrical.md`, `dept_sanitation.md`, `dept_traffic.md`, `dept_environmental.md`, `dept_general.md` | Pune Municipal Corporation (PMC), PWD Maharashtra | Organizational boundaries, jurisdiction limits, escalation chains, official helplines (1800 1030 222). |
| **Field SOPs** | `sop_pothole.md`, `sop_road_damage.md`, `sop_water_leakage.md`, `sop_sewage.md`, `sop_streetlight.md`, `sop_garbage.md`, `sop_illegal_dumping.md`, `sop_traffic_signal.md`, `sop_noise_pollution.md`, `sop_other.md` | IRC Standards, Central Public Health & Env Engineering Organisation (CPHEEO) | Repair workflows, cold-mix/mastic asphalt criteria, suction-cum-jetting safety, electrical pole grounding. |
| **Strategic Playbooks** | `playbook_pothole.md`, `playbook_open_manhole.md`, `playbook_waterlogging.md`, `playbook_sewage_overflow.md`, `playbook_encroachment.md`, `playbook_stray_animals.md`, etc. | Municipal Field Handbooks | 3-point rapid containment procedures, barricading norms, emergency field dispatch protocols. |
| **Statutory & Legal** | `legal_swm_rules.md`, `legal_plastic_waste.md`, `legal_pollution_acts.md`, `legal_rts_act.md`, `legal_rights.md`, `rti_guide.md`, `escalation_matrix.md` | Gazette of India, MoEFCC, DoPT, Maharashtra RTS Commission | Solid Waste Management Rules 2016 (3-stream segregation, bulk waste), Single-Use Plastic Ban thresholds (75μm / 120μm), Water Act 1974, Air Act 1981, RTI filing rules (3000 chars, fee exemptions, 30-day timeline, 48-hr life/liberty emergency). |
| **Disaster & Seasonal** | `disaster_urban_flooding.md`, `disaster_heatwave.md`, `disaster_fire_structural.md`, `seasonal_monsoon_prep.md`, `seasonal_summer_scarcity.md` | National Disaster Management Authority (NDMA) | Flood evacuation protocols, water supply reservoir management (Khadakwasla, Panshet, Varasgaon), pre-monsoon culvert desilting. |
| **Environmental & Health** | `env_air_quality.md`, `env_tree_protection.md`, `env_water_bodies.md`, `health_vector_borne.md`, `health_water_borne.md`, `health_stray_animal_control.md` | CPCB, MPCB, NVBDCP, Animal Birth Control (ABC) Rules | National Air Quality Index (NAQI) bands, Maharashtra Urban Areas Tree Protection Act, anti-larval spraying, rabies quarantine & PEP guidelines. |

---

### 2. Zero-Hallucination Policy & Provenance Verification
To ensure high civic fidelity, CivicPulse enforces strict information verification rules:
1. **Source Provenance Auditing**: Every data point in the knowledge base must map directly to an official government portal (`.gov.in`, `.nic.in`, `pmc.gov.in`, `mpcb.gov.in`).
2. **The `VERIFY` Filter Engine**: Any numerical deadline, direct desk phone extension, or fine amount that was not explicitly confirmed via live fetched web content during auditing is marked with a special inline token: `VERIFY`.
3. **Ingestion Purge**: When `rag/ingest.py` runs, **every line containing the `VERIFY` token is dropped** before vector embeddings are calculated. This guarantees that unconfirmed numbers or contact lines are never ingested into vector memory.
4. **Audit Reporting**: Dropped lines and warnings (missing URLs, files older than 365 days, short word counts) are automatically compiled into [knowledge/_REVIEW.md](file:///c:/Users/Asus/OneDrive/Desktop/CivicsPlus/Local%20Problem%20solving%20system/knowledge/_REVIEW.md) during ingestion.

---

### 3. Hierarchical Chunking & Ingestion Engine (`rag/ingest.py`)
Vector quality depends on context-preserving document chunking. Rather than naive fixed-character chunking, CivicPulse utilizes a **two-tier hierarchical splitting strategy**:

```
[Markdown Source File]
         │
         ▼
[YAML Frontmatter Extractor] ───> Extracts: title, type, city, source_url, last_verified
         │
         ▼
[VERIFY Line Filter] ───────────> Purges unverified claims & compiles _REVIEW.md
         │
         ▼
[MarkdownHeaderTextSplitter] ───> Splits text semantically on `## Section` boundaries
         │
         ▼
[RecursiveCharacterSplitter] ───> Splits large sections into chunks (700 chars, 100 overlap)
         │
         ▼
[Context Prefix Injection] ─────> Prepends: "[Document Title > Section Name]"
         │
         ▼
[FastEmbed ONNX Vectorizer] ────> Generates 384-dimensional dense float vector
         │
         ▼
[PGVector Batch Insertion] ─────> Writes to Supabase / PostgreSQL table `langchain_pg_embedding`
```

- **Metadata Enrichment**: Each vector chunk is tagged with JSONB metadata:
  ```json
  {
    "source": "sop_pothole.md",
    "title": "Standard Operating Procedure: Pothole Repair",
    "type": "sop",
    "category": "Pothole",
    "city": "Pune",
    "language": "en",
    "section": "Technical Repair Specifications",
    "source_url": "https://complaint.pmc.gov.in/home",
    "last_verified": "2026-10-18"
  }
  ```
- **Ingestion Lock**: Concurrency-guarded via `.ingest.lock` to prevent race conditions during bulk rebuilds.
- **Verification Integrity Check**: Automatically queries PostgreSQL at the end of ingestion to verify that chunk counts per type in the database match local markdown counts.

---

### 4. Dual-Engine Vector Retrieval (Direct SQL vs. LangChain)
CivicPulse supports two interchangeable vector retrieval backends (`RAG_BACKEND=sql` or `RAG_BACKEND=langchain`):

#### A. Direct SQL Vector Search (`retrieve_context_sql`, Default & Production-Recommended)
- Eliminates runtime LangChain overhead, reducing worker initialization time and memory usage.
- Uses native `psycopg` to query PostgreSQL with vector cosine distance (`<=>` operator):
  ```sql
  SELECT 
      e.document,
      e.cmetadata,
      1 - (e.embedding <=> %s::vector) AS score
  FROM langchain_pg_embedding e
  JOIN langchain_pg_collection c ON e.collection_id = c.uuid
  WHERE c.name = 'civic_kb'
  ORDER BY e.embedding <=> %s::vector
  LIMIT 10;
  ```
- **Strict Latency Budget**: Connect timeout is set to 5s, `statement_timeout` is locked to 3000ms, and total RAG retrieval budget is strictly capped at **4.0 seconds**. If the database or query rewrite lags, it gracefully falls back without blocking the application.
- **Relevance Filtering**: Only chunks with a similarity score $\ge 0.30$ are accepted.
- **Source Diversity**: Limits any single source document to a maximum of 2 chunks in the final context window to prevent one file from monopolizing the prompt.

#### B. LangChain Vector Store (`retrieve_context_langchain`)
- Integrated with `langchain-postgres` and `PGVector`.
- Used when deep LCEL (LangChain Expression Language) chaining or external LangChain tooling is configured.

#### C. Multilingual Query Rewriting
Citizens frequently search in Hindi, Marathi, or conversational Hinglish (e.g., *"Hamare galli me kachra jam gaya hai do hafte se"*). 
- The query rewriter (`rewrite_query()`) translates and extracts intent into a clean English search query (e.g., *"uncollected garbage accumulation residential alley solid waste management"*) before vector retrieval.
- If the rewriter experiences network latency or rate limits, it falls back to the original text without throwing an error.

---

### 5. Guardrails, Sanitization & Safe-Valve Memory Watcher

```
[User Question]
       │
       ▼
[Query Rewriting & Vector Search]
       │
       ▼
[Grounded Prompt Injection] ───> System instructions: "Answer ONLY using verified text below"
       │
       ▼
[LLM Inference (Groq)]
       │
       ▼
[Sanitize AI Claims] ──────────> Regex removes:
       │                         - Any mention of 'Greater Pune' or 'MCGP' (invalid names)
       │                         - Any time range (e.g. '24-48 hours') NOT in retrieved context!
       ▼
[Clean AI Text] ───────────────> Strips markdown clutter, <think> tags, formats clean bullets
       │
       ▼
[Final Output to Citizen / Admin]
```

1. **Safety Valve Memory Watcher (`is_rss_over_limit`)**:
   - Cloud containers (e.g. Render Free Tier) limit memory to 512MB RAM.
   - CivicPulse continuously monitors process Resident Set Size (RSS) via `/proc/self/status` or `psutil`.
   - If RSS exceeds `RAG_MAX_RSS_MB` (default: 440MB), RAG retrieval is **temporarily bypassed** for that request, logging a rate-throttled warning and preventing an out-of-memory container crash.
2. **Post-Generation Assertion Sanitizer (`sanitize_ai_claims`)**:
   - Inspects the generated text line by line.
   - Detects all generated time expressions (e.g., *"within 24 to 48 hours"*, *"in 3 to 5 days"*).
   - If that time interval does **not** appear in the retrieved context text, **the sentence is purged from the response**.
   - Removes incorrect municipal body references (e.g., "Greater Pune", "MCGP") and replaces them with the official **Pune Municipal Corporation (PMC)** designation.
3. **Markdown Formatter & Reasoning Stripper (`clean_ai_text`)**:
   - Automatically strips `<think>...</think>` internal chain-of-thought blocks generated by reasoning models (like Qwen).
   - Converts nested asterisks and header hashes into crisp typography with clean bullet points (`•`).

---

## 💾 Data Architecture: What Data We Store

CivicPulse uses a unified persistence layer managed through **SQLAlchemy 2.0 ORM** with automatic schema synchronization, supporting both **SQLite** (local development and single-container deployments) and **PostgreSQL** (production enterprise clusters).

### 1. Relational Matrix & Table Schemas

```
  ┌─────────────────────────┐             ┌─────────────────────────┐
  │          users          │             │       complaints        │
  ├─────────────────────────┤             ├─────────────────────────┤
  │ id (PK)                 │◄───┐   ┌───►│ id (PK)                 │
  │ fullname                │    │   │    │ user_id (FK)            │
  │ email, mobile           │    │   │    │ category, description   │
  │ username (UNIQUE)       │    │   │    │ priority, status        │
  │ password (scrypt hash)  │    │   │    │ latitude, longitude     │
  │ role (user | admin)     │    │   │    │ image_url, video_url    │
  │ trust_score (0-100)     │    │   │    │ image_embedding (BLOB)  │
  │ streak_days             │    │   │    │ ai_analysis             │
  │ last_active_date        │    │   │    │ ai_suggestion           │
  │ created_at              │    │   │    │ upvotes, affected_count │
  └─────────────────────────┘    │   │    │ department, ward        │
                                 │   │    │ status_step (1-4)       │
  ┌─────────────────────────┐    │   │    │ estimated_resolution    │
  │   complaint_upvotes     │    │   │    │ created_at, resolved_at │
  ├─────────────────────────┤    │   │    └─────────────────────────┘
  │ id (PK)                 │    │   │                 │
  │ complaint_id (FK)───────┼────┼───┘                 │
  │ user_id (FK)────────────┼────┘                     │
  │ created_at              │                          │
  └─────────────────────────┘                          ▼
                                          ┌─────────────────────────┐
  ┌─────────────────────────┐             │     issue_timeline      │
  │        comments         │             ├─────────────────────────┤
  ├─────────────────────────┤             │ id (PK)                 │
  │ id (PK)                 │             │ complaint_id (FK)       │
  │ complaint_id (FK)───────┼────────────►│ status                  │
  │ user_id (FK)            │             │ notes                   │
  │ parent_id (self-ref)    │             │ created_at              │
  │ content, author_name    │             └─────────────────────────┘
  │ created_at              │
  └─────────────────────────┘
```

#### Detailed Table Specifications

| Table Name | Primary Purpose | Fields Stored |
|---|---|---|
| `complaints` | Core grievance records filed by citizens or voice ingestion. | `id`, `category`, `description`, `priority` (`Low`, `Medium`, `High`, `Emergency`), `status` (`Pending`, `In Progress`, `Resolved`, `Rejected`), `location`, `latitude`, `longitude`, `created_at`, `resolved_at`, `ai_analysis` (triage summary), `ai_suggestion` (3-point tactical action plan), `official_response`, `upvotes`, `image_url`, `video_url`, `status_step` (1: Received, 2: Triaged, 3: Dispatched, 4: Resolved), `is_emergency`, `user_id`, `image_embedding` (binary vector), `department`, `estimated_resolution_time`, `resolution_confidence`, `ward`, `is_anonymous`, `affected_count`. |
| `users` | Citizen profiles, administrator accounts, and reputation metrics. | `id`, `fullname`, `mobile`, `email`, `username` (unique), `password` (cryptographic hash), `role` (`user` or `admin`), `created_at`, `trust_score` (Civic credit score, 0-100), `streak_days` (continuous civic engagement streak), `last_active_date`. |
| `issue_timeline` | Immutable chronological audit trail of all ticket state changes. | `id`, `complaint_id`, `status` (new state), `notes` (administrative rationale or contractor notes), `created_at`. |
| `comments` | Nested community discussions and citizen updates on active tickets. | `id`, `complaint_id`, `user_id`, `author_name`, `parent_id` (for threaded replies), `content`, `created_at`. |
| `complaint_upvotes` | Deduped citizen upvotes for neighborhood escalation thresholds. | `id`, `complaint_id`, `user_id`, `created_at` (unique constraint on `complaint_id + user_id`). |
| `issue_affected` | Counter for citizens directly impacted by a common civic issue. | `id`, `complaint_id`, `user_id`, `created_at` (unique constraint on `complaint_id + user_id`). |
| `complaint_subscribers` | Subscriptions for real-time notification alerts on specific tickets. | `id`, `complaint_id`, `user_id`, `created_at`. |
| `feedback` | Post-resolution citizen satisfaction audits and review scores. | `id`, `complaint_id`, `user_id`, `rating` (1 to 5 stars), `comment`, `created_at`. |
| `announcements` | Public bulletins, road closure notices, and seasonal warnings. | `id`, `title`, `content`, `author` (Admin department), `created_at`. |
| `user_badges` | Gamification achievements awarded to active citizens. | `id`, `user_id`, `badge_name` (`First Watch`, `Civic Guardian`, `Community Pillar`, etc.), `awarded_at`. |
| `workers` | Municipal field worker fleet telemetry and live assignments. | `name` (PK), `lat`, `lng` (real-time GPS coordinates), `assignment` (active complaint ID), `last_seen`. |
| `chat_history` | Persistent conversational history for citizen queries with AI agents. | `id`, `user_id`, `message`, `response`, `created_at`. |
| `weekly_summaries` | AI-generated executive briefings compiled for municipal leadership. | `id`, `summary`, `created_at`. |

---

### 2. Vector Space & Embedding Storage
When using PostgreSQL with the PGVector extension (configured via `SUPABASE_DB_URL`):
- **`langchain_pg_collection`**: Manages the `civic_kb` namespace collection.
- **`langchain_pg_embedding`**: Stores high-dimensional dense vector embeddings:
  - `uuid`: Unique chunk identifier.
  - `collection_id`: Foreign key reference to collection UUID.
  - `embedding`: 384-dimensional vector (`vector(384)`) generated by `all-MiniLM-L6-v2`.
  - `document`: The clean text chunk with header prefix.
  - `cmetadata`: JSONB dictionary containing frontmatter, source file, section, category, and audit metadata.

### 3. Lifecycle Telemetry & Timeline Auditing
Every ticket transitions through four defined lifecycle stages reflected in `status_step`:
1. **Step 1: Ingested & Verified**: Complaint registered via voice or web; AI completes triage, category allocation, and duplicate scanning.
2. **Step 2: Department Triaged**: Department assigned (e.g. *Road Maintenance Dept* or *Water Supply & Sewerage*); 3-point tactical action plan attached.
3. **Step 3: Crew Dispatched**: Field contractor or ward junior engineer assigned; worker GPS mapped and marked on live tracker.
4. **Step 4: Resolved & Audited**: Work verified on-site; resolution timestamp logged; citizen rating and feedback collected.

---

## 💻 Technology Stack Deep-Dive

CivicPulse is built with an optimized Python and native Web stack:

```
┌────────────────────────────────────────────────────────────────────────┐
│                          PRESENTATION LAYER                            │
│  Vanilla HTML5 + Modern CSS3 (Glassmorphism) + Vanilla ES6 JavaScript  │
│  Chart.js 4.x (Visual Analytics) • Lucide Icons • WebRTC Audio API     │
└────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        CORE APPLICATION BACKEND                        │
│  Flask 2.3+ (WSGI Application) • Gunicorn 21.x (Production Server)     │
│  Flask-WTF & CSRFProtect • Flask-Limiter (Rate Limiting)               │
│  Flask-SQLAlchemy 3.x & SQLAlchemy 2.0 (Relational Data Layer)         │
│  Werkzeug Security (scrypt Password Hashing)                           │
└────────────────────────────────────────────────────────────────────────┘
                  │                                    │
                  ▼                                    ▼
┌──────────────────────────────────┐ ┌───────────────────────────────────┐
│     AI & SPEECH INTELLIGENCE     │ │     VECTOR & RAG SUBSYSTEM        │
│ • Groq Cloud Inference Network   │ │ • FastEmbed (ONNX Runtime, 1 thr) │
│ • qwen/qwen3.8-27b (NLP & Triage)│ │ • sentence-transformers/all-      │
│ • LLaMA 3.2 Vision (Inspection)  │ │   MiniLM-L6-v2 (384-dim dense)    │
│ • Whisper Large-v3 (Speech2Text) │ │ • PostgreSQL + PGVector (<=> cos) │
│ • Multi-Key Round-Robin & Retry  │ │ • Supabase Cloud Database         │
└──────────────────────────────────┘ └───────────────────────────────────┘
                  │                                    │
                  ▼                                    ▼
┌──────────────────────────────────┐ ┌───────────────────────────────────┐
│     COMMUNICATIONS & SPATIAL     │ │       STORAGE & PERSISTENCE       │
│ • Brevo HTTP API (Transaction OTP│ │ • SQLite 3 (Dev / Volume Storage) │
│ • Twilio SMS API Gateway         │ │ • PostgreSQL 15+ (Production DB)  │
│ • Geopy (Geodesic 100m Proximity)│ │ • Docker / Fly.io / Render Ready  │
└──────────────────────────────────┘ └───────────────────────────────────┘
```

### Detailed Component Matrix

| Subsystem | Technology | Purpose & Implementation Details |
|---|---|---|
| **Web Server & Backend** | `Python 3.9+`, `Flask 2.3+`, `Gunicorn` | Core routing, Jinja2 template rendering, RESTful API endpoints, request filtering, and session management. |
| **Relational ORM** | `SQLAlchemy 2.0`, `Flask-SQLAlchemy` | Database abstraction wrapper. Uses parameterized SQL queries everywhere to prevent SQL injection vulnerabilities. Compatible with both SQLite and PostgreSQL without code changes. |
| **Vector Engine** | `FastEmbed`, `ONNX Runtime` | Generates 384-dimensional dense vectors using `sentence-transformers/all-MiniLM-L6-v2`. **Runs via ONNX without PyTorch**, consuming under 50MB of RAM and executing in a single thread to guarantee stability on 512MB hosting plans. |
| **Vector Database** | `PostgreSQL`, `PGVector`, `Supabase` | Persistent vector table `langchain_pg_embedding` indexed with cosine distance operators (`<=>`). |
| **AI Inference** | `Groq Cloud API` | Provides low-latency inference across `qwen/qwen3.8-27b`, Meta LLaMA 3.2 Vision, and Whisper Large-v3. Built with multi-key round-robin load balancing and automatic failover backoff. |
| **Audio Transcription** | `Groq Whisper Large-v3` | High-fidelity multilingual speech-to-text. Processes webm/wav audio files from WebRTC browser recordings in real time. |
| **Computer Vision** | `LLaMA 3.2 Vision` | Inspects photographic evidence uploaded by citizens to classify the problem type and verify physical degradation. |
| **Geospatial Engine** | `Geopy` | Computes geodesic distance (Vincenty/Great-Circle) between incoming coordinates to flag duplicate tickets within 100 meters. |
| **Email Verification** | `Brevo HTTP API` (Sendinblue) | Sends cryptographic 6-digit OTP verification emails via HTTP REST API, avoiding cloud SMTP port blocks (ports 25/587). |
| **Rate Limiting** | `Flask-Limiter` | Enforces client IP throttling: 1000 requests/day, 200 requests/hour globally, 10 requests/minute on voice ingestion, and 20 requests/minute on RAG endpoints. |
| **Frontend Styling** | `Vanilla CSS3`, `animations.css` | Bespoke 3D glassmorphic styling system. Features 28+ CSS/JS micro-animations, 3D card tilt, parallax scrolling, and responsive layouts without bulky UI framework dependencies. |
| **Data Visuals** | `Chart.js 4.x` | Interactive canvas charts rendering department resolution ratios, daily intake trends, and grievance category distributions. |

---

## 🚀 Core Platform Modules

### 1. Voice-First AI Reporting Engine
- **WebRTC Native Capture**: Citizens tap the microphone icon to record spoken grievances in their mother tongue (Marathi, Hindi, English, Hinglish).
- **Whisper Ingestion**: Audio is streamed to Groq Whisper Large-v3 for instantaneous phonetic transcription.
- **Structured JSON Synthesis**: The raw transcript is passed to the LLM with a strict prompt contract, extracting:
  - `category`: Standardized municipal category (Pothole, Sewage, Water Leakage, Streetlight, etc.).
  - `clean_description`: Professional, formatted municipal complaint narrative.
  - `priority`: Autonomous assessment (`Low`, `Medium`, `High`, `Emergency`).
  - `native_transcript`: Original citizen utterance preserved for administrative audit.
- **Instant Fallback**: If LLM inference is rate-limited, an instant regex/keyword heuristic engine ensures that the complaint is still structured without error.

---

### 2. AI Computer Vision Evidence Inspector
- Citizens can upload photographic or video evidence with their reports.
- Evidence is processed via **LLaMA 3.2 Vision** on Groq:
  - Validates that the photo represents an actual civic infrastructure issue (discarding memes, selfies, or unrelated images).
  - Flags severe structural hazards (e.g. exposed live high-voltage wiring, missing manhole covers on unlit streets) and automatically marks the ticket as `is_emergency = 1`.

---

### 3. Semantic & Geodesic Deduplication
To prevent municipal departments from being flooded with dozens of tickets for the same incident:
- When a new complaint is filed with GPS coordinates, CivicPulse queries all active tickets within a **100-meter geodesic radius** (`geopy.distance.geodesic`).
- In environments with available memory, text semantic similarity is computed using dense vector cosine distance.
- If an existing open ticket is found within the radius:
  - The citizen's report is linked to the existing master issue.
  - The master issue's `upvotes` and `affected_count` are automatically incremented.
  - The citizen is registered as a subscriber to receive resolution notifications when the master issue is resolved.

---

### 4. CivicIQ City Assistant & RTI Generator
Accessible via `/civic-iq`, this module acts as a virtual municipal advisor for citizens:
- **City Diagnostic Scanner**: Citizens can enter any Indian city name (e.g., Pune, Mumbai, Bengaluru, Nagpur) to receive a synthesized civic intelligence report:
  - Overall Municipal Health Score (0-100) and infrastructure grade.
  - Top 5 urban bottlenecks for that city.
  - Responsible departments, municipal contact numbers, and relevant legal rights.
- **RTI Application Generator**: Automatically drafts a complete, legally compliant **Right to Information (RTI) application** tailored to the citizen's specific grievance, citing appropriate sections under the RTI Act 2005.
- **Hierarchical Escalation Matrix**: Outlines the progression path from Ward Junior Engineer up to the Municipal Commissioner and State Grievance Portals (Aaple Sarkar / CPGRAMS).

---

### 5. Municipal Admin Command Center
Accessible to authenticated administrators via `/dashboard`:
- **Real-Time Triage Grid**: Live view of pending grievances with automated priority color-coding.
- **3-Point Tactical Action Plans**: Clicking any complaint displays an AI-generated containment strategy grounded in the verified SOP for that category:
  1. *Immediate Containment* (e.g., barricading, cordoning, warning lights).
  2. *Physical Repair Procedure* (e.g., tack coat application, cold-mix compaction, pressure testing).
  3. *Post-Repair Verification* (e.g., slump test, road level alignment, photographic sign-off).
- **Viral Outrage & Sentiment Radar**: Evaluates incoming complaint text for citizen frustration levels, flagging volatile grievances before they attract media escalation.
- **Municipal Fleet Tracker**: Live tracking of field workers (`lat`/`lng`), their current work assignments, and real-time dispatching.
- **One-Click Mayoral Executive Briefing**: Synthesizes weekly municipal metrics into an executive summary ready for departmental commissioners.

---

### 6. LivePulse City Dashboard & Gamification
Accessible via `/live-pulse` and `/community`:
- **Transparent Public Telemetry**: Displays municipal resolution rates, average turnaround times, and open vs. closed ticket counts.
- **Interactive Ward Map**: Visualizes grievance clusters across municipal wards.
- **Citizen Trust Score (0-100)**: Users earn trust points for verified reporting, helpful comments, and confirmed resolutions, while frivolous complaints deduct points.
- **Civic Badges**: Citizens unlock badges (*"First Watch"*, *"Pothole Patrol"*, *"Civic Guardian"*) as they help improve their neighborhoods.
- **Community Upvoting**: Neighborhood residents upvote pressing issues, escalating high-priority tickets to admin attention once an upvote threshold is reached.

---

## 🛡️ Security, Privacy & Reliability

CivicPulse is engineered with defense-in-depth security principles:

1. **CSRF Protection**: Every state-modifying request (`POST`, `PUT`, `DELETE`) is guarded by **Flask-WTF CSRF tokens**. Tokens are validated both from form data and AJAX HTTP headers (`X-CSRFToken` / `X-CSRF-Token`).
2. **Strict Role-Based Access Control (RBAC)**: Clear separation between standard citizens and municipal administrators. Administrative routes (`/dashboard`, `/admin/*`, `/api/rag/status`) enforce strict session verification.
3. **Cryptographic Password Hashing**: Passwords are never stored in plaintext; they are securely hashed using `werkzeug.security` (scrypt / pbkdf2:sha256).
4. **Parameterized Database Queries**: All database operations use SQLAlchemy parameterized placeholders (`:p0`, `:p1`), eliminating SQL injection attack surfaces.
5. **Multi-Tier Rate Limiting**: Managed by `Flask-Limiter` with in-memory storage to prevent denial-of-service (DoS) bursts against expensive AI nodes.
6. **HTTP Security Headers**: Injected automatically on every response:
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: SAMEORIGIN`
   - `Referrer-Policy: strict-origin-when-cross-origin`
   - Secure cookie flags (`HttpOnly`, `SameSite=Lax`, `Secure` in production).
7. **Safe-Valve Memory Watchdog**: Pre-empts Linux OOM killer termination on 512MB RAM instances by dynamically pausing vector search if system RSS memory exceeds 440MB.
8. **Automated Error Logging**: Critical exceptions are routed to a self-pruning rotating log handler (`app_errors.log`, 100KB max, 3 backups).

---

## 🔌 REST API Reference

### Citizen & Public Endpoints

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/voice-report` | Uploads WebRTC audio file; transcribes and returns structured JSON complaint. | Optional |
| `POST` | `/api/rag/ask` | Queries the verified municipal knowledge base; returns grounded answer with source citations. | Yes (User) |
| `POST` | `/api/civic-iq/scan` | Generates a city diagnostic report with health score, top issues, and RTI template. | No |
| `POST` | `/api/chat` | Conversational civic chatbot assistant endpoint. | Yes (User) |
| `POST` | `/upvote/<int:id>` | Upvotes an active community grievance. | Yes (User) |
| `POST` | `/api/feedback/<int:id>` | Submits post-resolution star rating (1-5) and qualitative feedback. | Yes (User) |

### Administrative & Monitoring Endpoints

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/rag/status` | Returns operational status of RAG: backend type, loaded chunks per type, RSS memory, and last retrieval latency. | Yes (Admin) |
| `POST` | `/update_status/<int:id>` | Updates complaint lifecycle step (1 to 4) and appends official response notes. | Yes (Admin) |
| `POST` | `/api/admin/dispatch` | Dispatches a municipal field worker to a specific grievance location. | Yes (Admin) |
| `GET` | `/export_csv` | Streams all municipal grievance records as a downloadable CSV report. | Yes (Admin) |

---

## ⚙️ Installation & Setup Guide

### Prerequisites
- **Python 3.9, 3.10, or 3.11**
- **Git**
- **PostgreSQL 14+** (with `pgvector` extension) *OR* a free [Supabase](https://supabase.com/) project. (For lightweight local testing, SQLite is supported out of the box).
- **Groq Cloud API Key** (from [console.groq.com](https://console.groq.com/)).

---

### Step 1: Clone Repository & Create Virtual Environment
```bash
# Clone the repository
git clone https://github.com/parthdahiphale6363-ui/CivicPulse.git
cd CivicPulse

# Create a Python virtual environment
python -m venv venv

# Activate virtual environment
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On macOS / Linux:
source venv/bin/activate
```

---

### Step 2: Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

### Step 3: Configure Environment Variables
Create a `.env` file in the project root (copy from `.env.example`):
```bash
cp .env.example .env
```

Configure the following variables in `.env`:
```env
# Flask Application Security
SECRET_KEY=your_cryptographically_secure_random_key_here
FLASK_ENV=development

# Groq Cloud AI Keys (Supports multiple comma-separated keys for automatic round-robin failover)
GROQ_API_KEY=gsk_your_primary_groq_api_key_here,gsk_your_backup_groq_api_key_here
GROQ_RAG_MODEL=qwen/qwen3.8-27b

# Relational Database Connection (Defaults to local SQLite if omitted)
# Format for PostgreSQL: postgresql+psycopg2://user:password@host:port/dbname
DATABASE_URL=sqlite:///database.db

# RAG & Vector Database Settings
# Set to '1' to enable verified RAG retrieval; '0' runs in lightweight mode
RAG_ENABLED=1
# 'sql' (Recommended, lightweight direct vector query) or 'langchain'
RAG_BACKEND=sql
# Connection string for Supabase / PostgreSQL with pgvector:
SUPABASE_DB_URL=postgresql://postgres:your_supabase_password@db.your_project.supabase.co:5432/postgres
# Safety valve memory threshold in MB (prevents OOM on 512MB hosting)
RAG_MAX_RSS_MB=440

# Email Verification (Brevo HTTP API for real OTP delivery)
BREVO_API_KEY=your_brevo_api_key_here

# Administrative Bootstrap (Optional)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change_this_secure_password
```

---

### Step 4: Ingest the Municipal Knowledge Base into PGVector
Before using the RAG query engine, populate your vector database with the 50+ audited knowledge manuals:
```bash
# Run ingestion (processes Markdown files, strips VERIFY tokens, indexes into PGVector)
python -m rag.ingest --yes
```

Expected output:
```
=======================================================
 CIVICPULSE MUNICIPAL KNOWLEDGE BASE INGESTOR
=======================================================
Target Database Host: db.your_project.supabase.co
Target Port         : 5432
Collection Name     : civic_kb
=======================================================
Processing 50+ knowledge files from /knowledge...
Chunk counts per type (local):
  - department     : 42 chunk(s)
  - disaster       : 28 chunk(s)
  - env            : 24 chunk(s)
  - health         : 26 chunk(s)
  - infra          : 32 chunk(s)
  - legal          : 38 chunk(s)
  - playbook       : 64 chunk(s)
  - seasonal       : 18 chunk(s)
  - sop            : 74 chunk(s)
  Total chunks     : 346+
[VERIFIED] Database contains matching chunks across all categories.
[SUCCESS] Ingestion completed successfully!
```

---

### Step 5: Launch the Application
```bash
# Run local development server
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 🌐 Deployment Strategies

CivicPulse is containerized and pre-configured for one-click deployment across major cloud providers:

### A. Docker Deployment
```bash
# Build the Docker image
docker build -t civicpulse:latest .

# Run container with environment file
docker run -d -p 5000:5000 --env-file .env --name civicpulse_app civicpulse:latest
```

### B. Render / Fly.io Configuration
- **Procfile**: Included (`web: gunicorn wsgi:app --workers 2 --threads 4 --timeout 120`).
- **render.yaml**: Included in repository for infrastructure-as-code deployment.
- **fly.toml**: Pre-configured with volume mount points at `/data` for SQLite persistence across restarts.

---

## 👥 Contributors & Civic Impact

CivicPulse was created to empower citizens and elevate public administration through ethical, grounded, and transparent artificial intelligence.

- **Developer**: Parth Dahiphale ([@parthdahiphale6363-ui](https://github.com/parthdahiphale6363-ui))
- **Organization**: CivicPulse Municipal Innovation Lab
- **License**: MIT Open Source License

---

<div align="center">
  <sub>Built with ❤️ for resilient cities, responsive governance, and empowered citizens.</sub>
</div>
