# PULSE — AI-Enabled Civic Sentiment Analytics
### Rajkot Municipal Corporation (RMC) | Problem ID: PS000158

> **PULSE** (*Public Listening for Urban Service Excellence*) is an AI-enabled municipal intelligence platform designed for the **Rajkot Municipal Corporation (RMC)**. It ingests, normalizes, analyzes, and surfaces citizen feedback across multiple channels (WhatsApp Business Cloud API, official complaint spreadsheets, citizen portals, and social media) without storing personal citizen identifiers.

---

## 🏛️ Official RMC Master Data Synchronization

PULSE's database and analytics hierarchy are synchronized with the official [RMC Complaint Registration Portal](https://www.rmc.gov.in/ComplaintRegistration) and the official RMC dataset (`Complaint Details 01-10-2026 to 10-10-2026.xlsx` containing 13,535 verified records):

- **15 Official Municipal Departments:**
  - `DRAINAGE CHOCKUP/OVERFLOW` (Main lines, manhole choking, sewer flooding)
  - `ROSHNI BRANCH` (Street lighting, dark corridors, LED fixtures)
  - `SOLID WASTE MANAGEMENT` (Door-to-door tipper vans, community bins, sweeping)
  - `WATER WORKS(OUTDOOR)` (Pipeline leaks, contaminated water, low pressure)
  - `DRAINAGE MAINTENANCE` (Manhole leveling, chamber cover repair)
  - `BANDHKAM` (Roads, potholes, bitumen resurfacing, paver blocks, civil works)
  - `CITY BUS (RAJKOT RAJPATH)` (BRTS and City bus transit)
  - `A.N.C.D. (DOG & ANIMAL CONTROL)` (Catch stray cattle / *dhor pakadva*, dog nuisance)
  - `CONSERVANCY (DEAD ANIMAL)` (Emergency carcass removal)
  - `DABAN HATAV BRANCH` (Encroachment removal)
  - `HEALTH & URBAN MALERIYA` (Vector control, mosquito fogging)
  - `GARDEN & SPORTS` (Public parks, tree cutting)
  - `TOWN PLANNING & ESTATE` (Building permissions, layout violations)
  - `FOOD & SANITATION` (Food quality inspection, restaurant hygiene)
  - `TRAFFIC & TRNS. CELL` (Traffic signals, road markings, speed breakers)
- **18 Wards & 3 Administrative Zones:**
  - **West Zone:** Wards 1, 8, 9, 10, 11, 12 *(132 official neighborhood areas)*
  - **Central Zone:** Wards 2, 3, 7, 13, 14, 17 *(143 official neighborhood areas)*
  - **East Zone:** Wards 4, 5, 6, 15, 16, 18 *(74 official neighborhood areas)*
- **102 Official Complaint Categories:** Directly mapped to RMC complaint taxonomy.

---

## 🔒 Privacy & Data Minimization Safeguards

1. **Zero Citizen PII Stored:** Citizen names and mobile phone numbers (such as Columns 6 & 7 in official Excel exports) are **never stored** in the database.
2. **One-Way Cryptographic Hashes:** Messaging IDs and complaint numbers are converted into salted `SHA-256` hashes strictly for thread continuity.
3. **Zero Citizen Email Rule:** The application contains **no outbound communication channels to citizens**. All email alerts are dispatched **exclusively to opted-in municipal personnel**.
4. **Content Deduplication:** Duplicate ingestion from bots or repeated submissions is blocked via deterministic `SHA-256` content hashing.

---

## 🚀 Quickstart Local Setup Instructions

### 1. Prerequisites
- Python 3.9+ installed
- SQLite (included by default)

### 2. Activate Virtual Environment & Install Dependencies
```bash
# Navigate to project directory
cd "/Users/suhaniparmar/Documents/PULSE - Public Listening for Urban Service Excellence"

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Apply Database Migrations
```bash
python manage.py migrate
```

### 4. Load Official RMC Metadata & Seed Demo Data
```bash
# 1. Sync official RMC departments, wards, and complaint categories
python manage.py sync_official_rmc_metadata

# 2. Seed initial demo users, feedback items, and trend alerts
python manage.py seed_demo_data
```

### 5. Launch Local Development Server
```bash
python manage.py runserver 127.0.0.1:8000
```
Open your browser and navigate to:
- **Executive Dashboard:** `http://127.0.0.1:8000/dashboard/`
- **Feedback Inbox:** `http://127.0.0.1:8000/feedback/`
- **Ward Analytics:** `http://127.0.0.1:8000/analytics/locations/`
- **Department Analytics:** `http://127.0.0.1:8000/analytics/departments/`
- **Trends & Alerts:** `http://127.0.0.1:8000/alerts/`
- **Integrations Hub:** `http://127.0.0.1:8000/integrations/`
- **Staff Login:** `http://127.0.0.1:8000/accounts/login/`
- **Django Admin:** `http://127.0.0.1:8000/admin/`

---

## 🔑 Demo Personas & Credentials

| Persona / Role | Username | Password | Access Scope |
| :--- | :--- | :--- | :--- |
| **Municipal Commissioner / Admin** | `commissioner` | `RMCpulse2026!` | Citywide view across all 15 departments and 18 wards. |
| **Department Head (Drainage)** | `ee_drainage` | `RMCpulse2026!` | Scoped to Drainage Chockup/Overflow complaints. |
| **Ward Officer (Ward 10)** | `ward10_officer` | `RMCpulse2026!` | Scoped to Ward 10 (150 Feet Ring Road / Mavdi). |

---

## ⚙️ Environment Variables (`.env`)

Create a `.env` file in the project root:

```ini
# Core Django Configuration
DEBUG=True
SECRET_KEY=rmc-pulse-secure-key-replace-in-production
ALLOWED_HOSTS=localhost,127.0.0.1,testserver

# Database Configuration (Default: SQLite; Switchable to PostgreSQL)
DATABASE_URL=sqlite:///db.sqlite3
# DATABASE_URL=postgres://rmc_user:rmc_password@localhost:5432/rmc_pulse

# Meta WhatsApp Business Cloud API Configuration
WHATSAPP_PHONE_NUMBER_ID=109283746192
WHATSAPP_ACCESS_TOKEN=your_meta_system_user_access_token
WHATSAPP_VERIFY_TOKEN=rmc_secure_verify_token_2026
WHATSAPP_APP_SECRET=your_meta_app_secret_for_hmac_sha256

# Municipal Staff Email Notifications (SMTP / SES)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.rmc.gov.in
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=pulse-alerts@rmc.gov.in
EMAIL_HOST_PASSWORD=your_secure_smtp_password
DEFAULT_FROM_EMAIL=PULSE Urban Intelligence <pulse-alerts@rmc.gov.in>
```

---

## 🔌 Ingestion Connectors Status

| Connector Name | Channel Type | Status | Implementation Details |
| :--- | :--- | :--- | :--- |
| **CSV & Excel Importer** | `FILE_IMPORT` | **LIVE & ACTIVE** | Ingests generic CSVs and official RMC Excel exports (`Complaint Details 01-10-2026 to 10-10-2026.xlsx`). Discards citizen names and phones, deduplicates via SHA-256, runs AI analysis. |
| **WhatsApp Business Platform** | `WHATSAPP` | **LIVE & ACTIVE** | Official Meta Cloud API webhook endpoint (`/api/v1/integrations/whatsapp/webhook/`). Supports GET verification handshake and POST HMAC-SHA256 signature verification. |
| **Twitter / X API v2** | `TWITTER_X` | **SCAFFOLDING READY** | Scaffolding prepared for official `@myrmc_rajkot` mentions via Bearer Token. Zero unauthenticated scraping. |
| **Meta (Facebook & IG)** | `FACEBOOK` | **SCAFFOLDING READY** | Scaffolding prepared for official RMC Facebook page webhooks awaiting Page Access Token. |
| **RMC Grievance Portal** | `RMC_PORTAL` | **BUILT, AWAITING RMC ENDPOINT** | Live pull (`python manage.py sync_rmc_portal`, schedule via cron) of new complaints from an authorised RMC JSON feed, so no manual export is needed. Dedupes, discards citizen name/mobile, runs AI analysis. Needs the RMC API endpoint/token set in the admin (ConnectorConfig). Tested against a mocked feed only. |

---

## 🧪 Automated Verification Suite

Run the full end-to-end regression test suite:

```bash
python tests_phase5_verification.py
```

### Verification Checks Performed:
1. **Authentication & Roles:** Staff session login and RBAC verification.
2. **Multilingual AI:** Gujarati, Hindi/Hinglish, English, and Gujlish accuracy.
3. **Location Grounding:** Zero-hallucination verification against 349 Rajkot landmarks.
4. **Deduplication:** Automatic rejection of duplicate feedback submissions via SHA-256 content hashing.
5. **Meta WhatsApp Handshake & Security:** GET token verification and HMAC-SHA256 signature validation.
6. **Trend Detection:** Rolling baseline evaluation and volume spike detection ($\ge 2.0\times$ baseline).
7. **Staff-Only Notifications:** Idempotency checks and verification of zero citizen emails.
8. **Human-in-the-Loop Review:** Reclassification, Flying Squad remarks, and audit trail logging.
9. **Personal Data Minimization:** Verification that zero citizen names or phone numbers are stored.
10. **UI Health:** HTTP 200 OK across all municipal dashboard endpoints.

---

## ⚡ FastAPI WhatsApp Webhook Integration

The repository includes a dedicated FastAPI backend service at `fastapi_app/` with Meta webhook verification, HMAC-SHA256 signature checking, separate delivery/status parsing, and message deduplication.

### 1. Configuration (`.env`)
Configure your Meta variables (refer to `.env.example`):
```bash
WHATSAPP_VERIFY_TOKEN=rmc_civicpulse_verify_token_2026
WHATSAPP_APP_SECRET=your_meta_app_secret_here
WHATSAPP_ACCESS_TOKEN=your_meta_system_user_access_token_here
WHATSAPP_PHONE_NUMBER_ID=your_whatsapp_phone_number_id_here
```

### 2. Local Endpoint Path
- **GET & POST:** `http://127.0.0.1:8000/api/whatsapp/webhook`

### 3. Running FastAPI Locally
```bash
source .venv/bin/activate
uvicorn fastapi_app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 4. Exposing via HTTPS Tunnel for Meta Webhook Testing
Meta requires a public HTTPS URL. You can use **ngrok** or **Cloudflare Tunnel**:

```bash
# Option A: Using ngrok
ngrok http 8000

# Option B: Using Cloudflare Tunnel
cloudflared tunnel --url http://127.0.0.1:8000
```
- **Meta Callback URL:** `https://<your-tunnel-domain>/api/whatsapp/webhook`
- **Verify Token:** `rmc_civicpulse_verify_token_2026` (or value of `WHATSAPP_VERIFY_TOKEN`)

### 5. Running Webhook Unit Tests
```bash
pytest tests/test_whatsapp_webhook.py -v
```
Tests cover:
- GET verification challenge handshake (success + token/mode failure)
- POST HMAC-SHA256 signature validation (success + invalid/missing signature)
- Incoming text message parsing with SHA-256 phone pseudonymization (Zero PII)
- Delivery & status event parsing (`delivered`, `read`) separated from citizen complaints
- Duplicate message ID rejection
- Malformed JSON error safety

---

## 🔮 Future Scope — Scalable Enterprise Data Processing

To support enterprise municipal scale handling tens of thousands of citizen complaints daily across Rajkot, the architecture is designed for progressive expansion into a distributed, event-driven data processing pipeline:

### 1. Asynchronous Ingestion & Task Queue (Celery + Redis)
- **Decoupled Architecture:** Incoming complaints from Social Media (Twitter/X, Facebook), Gmail, and the RMC Portal are acknowledged immediately (`HTTP 202 Accepted`) and pushed to an in-memory Redis message broker.
- **Worker Queues:** Celery workers process heavy NLP, classification, and GIS operations asynchronously in background task queues:
  - `tasks.detect_language`: Multilingual Gujarati/Hindi/English tokenization.
  - `tasks.sentiment_analysis`: Evidence-based sentiment scoring without API latency.
  - `tasks.categorize_complaint`: Department routing and severity assessment.
  - `tasks.geocode_location`: Gazetteer matching against 349 Rajkot municipal landmarks.
- **Fault Tolerance & Retries:** Automatic exponential backoff retries with dead-letter queues (DLQ) for failed connector syncs or rate-limited webhooks.

### 2. High-Performance Enterprise Relational Database (PostgreSQL)
- **Primary Data Store:** Migration from development SQLite to production-grade PostgreSQL 16+.
- **Optimized Indexing:**
  - `B-Tree` composite indexes on `(source_type, source_platform, published_at)`.
  - `GIN` indexes on `raw_metadata` (`JSONB`) for high-speed technical query filtering.
  - `Trigram (pg_trgm)` indexes on `raw_text` for instantaneous multilingual search across Gujarati and English.
- **Connection Pooling:** Integrated PgBouncer for handling hundreds of concurrent staff and intake connections.

### 3. Bulk Ingestion, Keyset Pagination & Performance Monitoring
- **Bulk Operations:** `bulk_create` and batch ingestion pipeline processing up to 5,000 records per transaction chunk during spreadsheet imports.
- **Keyset / Cursor Pagination:** Prevents performance degradation on large tables with millions of complaints.
- **Observability:** Prometheus metrics exporter and Flower dashboard for real-time monitoring of Celery worker queues, task throughput, latency, and system health.


