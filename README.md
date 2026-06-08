# Looker Studio Data Pipeline

An end-to-end automated data pipeline that ingests heterogeneous text data from multiple sources — REST APIs, webhooks, and web scrapers — on a 12-hour schedule, processes it through ETL with AI-powered tagging, persists it in Google BigQuery, and surfaces insights via Looker Studio dashboards.

## Business Problem Solved

Every data team faces the same exhausting cycle: manually exporting CSV exports from APIs, copying webhook payloads into spreadsheets, running one-off scrapers, then spending hours cleaning and re-formatting data before it ever reaches a dashboard. For teams managing multiple text data sources, this can consume 5–10 hours per week of analyst time just to keep the pipeline fed.

This project automates that entire workflow end-to-end. Incoming data from any combination of APIs, webhooks, or scraping tools is received by a FastAPI service, buffered in Google Cloud Storage, then processed every 12 hours by an Airflow DAG that normalises the schema, applies AI-generated tags using embedding similarity, and upserts everything into BigQuery. From there, Looker Studio connects directly to BigQuery for live, refreshable dashboards — no manual exports, no stale data.

The result: analysts see fresh data every 12 hours automatically, engineers spend zero time on ad-hoc data plumbing, and the whole pipeline is observable, auditable, and replayable from Airflow.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Looker Studio                                │
│                    (dashboards, reports)                            │
└──────────────────────────────▲──────────────────────────────────────┘
                               │ (live BigQuery queries)
┌──────────────────────────────▼──────────────────────────────────────┐
│                       Google BigQuery                                │
│              Dataset: looker_pipeline / Table: raw_data             │
│         (partitioned by ingested_at, clustered by source)          │
└──────────────────────────────▲──────────────────────────────────────┘
                               │ (upsert via google-cloud-bigquery)
┌──────────────────────────────▼──────────────────────────────────────┐
│                   Apache Airflow  (2.9)                             │
│  DAG: etl_pipeline   Schedule: every 12 hours                       │
│                                                                      │
│  fetch_gcs_blobs → run_etl → upsert_bigquery → cleanup_gcs_blobs    │
└──────────────────────────────▲──────────────────────────────────────┘
                               │ (read staged blobs)
┌──────────────────────────────▼──────────────────────────────────────┐
│                   Google Cloud Storage                              │
│                 Bucket: <GCS_BUCKET>                                │
│            (buffer for raw ingested records)                        │
└──────────────────────────────▲──────────────────────────────────────┘
                               │ (write raw JSON blobs)
┌──────────────────────────────▼──────────────────────────────────────┐
│                   FastAPI  (port 8080)                              │
│                                                                      │
│  POST /ingest        → validate, write to GCS                       │
│  POST /ingest/batch  → batch validate, write to GCS                 │
│  POST /webhook       → normalise envelope, write to GCS            │
│  GET  /health       → liveness probe                                │
└─────────────────────────────────────────────────────────────────────┘
         ▲                  ▲                   ▲
         │                  │                   │
   REST API calls     GitHub/GitLab       Scraping tools
   (httpx client)    webhooks            (BeautifulSoup)
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Ingest API | FastAPI 0.111 / Uvicorn |
| Scheduler and Orchestration | Apache Airflow 2.9 |
| Cloud Storage (buffer) | Google Cloud Storage |
| Data Warehouse | Google BigQuery |
| BI and Visualisation | Looker Studio |
| ETL | Pandas 2.2 |
| AI Tagging | sentence-transformers (HuggingFace) |
| Containerisation | Docker + Docker Compose |
| Configuration | python-dotenv |

## Getting Started

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- GCP project with BigQuery and GCS APIs enabled
- GCP Service Account key with `bigquery.dataEditor` and `storage.objectAdmin` roles

### Clone and install dependencies

```bash
# Clone the repo
git clone <your-repo-url>
cd looker-studio-pipeline

# Create and activate a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### Environment variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:

```
GCP_PROJECT_ID=your-gcp-project-id
GCP_BIGQUERY_DATASET=looker_pipeline
GCP_BIGQUERY_TABLE=raw_data
GCP_SERVICE_ACCOUNT_KEY=./gcp-key.json
GCS_BUCKET=your-gcs-bucket-name
AIRFLOW_HOME=./airflow
API_PORT=8080
LOG_LEVEL=INFO
AI_TAGGER_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

### GCP Authentication

Place your service account key JSON file at the path specified by `GCP_SERVICE_ACCOUNT_KEY` (default: `./gcp-key.json`). Ensure the service account has:

- `roles/bigquery.dataEditor` — for writing to BigQuery
- `roles/storage.objectAdmin` — for reading/writing GCS blobs

```bash
export GOOGLE_APPLICATION_CREDENTIALS="./gcp-key.json"
```

### Database setup (BigQuery)

The pipeline auto-creates the table on first run. To provision manually:

```sql
CREATE TABLE IF NOT EXISTS `your-project.looker_pipeline.raw_data`
(
  id          STRING    NOT NULL,
  source      STRING    NOT NULL,
  content     STRING,
  title       STRING,
  url         STRING,
  tags        STRING,
  ingested_at TIMESTAMP NOT NULL,
  processed_at TIMESTAMP,
  dag_run_id  STRING
)
PARTITION BY DATE(ingested_at)
CLUSTER BY source;
```

### Run locally

```bash
# Start the FastAPI ingest service
uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload

# In another terminal, start Airflow (using standalone for dev)
airflow standalone
```

### Docker Compose (full stack)

```bash
docker compose up --build
```

This starts both the FastAPI ingest service (port 8080) and Airflow (port 8081).

## API Overview

| Method | Path | Description |
|--------|------|-------------|
| POST | /ingest | Receive a single text record (JSON body) |
| POST | /ingest/batch | Receive multiple records at once |
| POST | /webhook | Webhook receiver (GitHub-style event envelope) |
| GET | /health | Liveness probe |

### Example: POST /ingest

```bash
curl -X POST http://localhost:8080/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "source": "api",
    "content": "Breaking: AI model scores 95% on medical board exam",
    "title": "AI Medical Board Results",
    "url": "https://news.example.com/ai-medical"
  }'
```

Response `201 Created`:

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "source": "api",
  "ingested_at": "2026-06-08T12:00:00Z",
  "status": "buffered"
}
```

### Example: POST /ingest/batch

```bash
curl -X POST http://localhost:8080/ingest/batch \
  -H "Content-Type: application/json" \
  -d '{
    "records": [
      {"source": "api", "content": "Record 1", "title": "Title 1"},
      {"source": "scraper", "content": "Record 2", "title": "Title 2"}
    ]
  }'
```

Response `201 Created`:

```json
{
  "ingested": 2,
  "ids": ["uuid-1", "uuid-2"],
  "status": "buffered"
}
```

### Example: POST /webhook

```bash
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: push" \
  -d '{
    "commits": [{"message": "fix: resolve auth bug"}],
    "repository": {"full_name": "org/repo"}
  }'
```

Response `200 OK`:

```json
{
  "id": "webhook-a1b2c3d4",
  "source": "webhook",
  "event_type": "push",
  "ingested_at": "2026-06-08T12:00:00Z",
  "status": "buffered"
}
```

## Project Structure

```
looker-studio-pipeline/
├── api/                        # FastAPI ingest service
│   ├── __init__.py
│   ├── main.py                 # App factory, CORS, exception handlers
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py          # Pydantic request/response models
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── health.py           # GET /health
│   │   └── ingest.py           # POST /ingest, /ingest/batch, /webhook
│   └── services/
│       ├── __init__.py
│       ├── bigquery.py         # BigQuery upsert logic
│       └── gcs_writer.py       # GCS blob staging
├── dags/
│   ├── __init__.py
│   └── etl_pipeline.py         # Airflow DAG definition
├── lib/
│   ├── __init__.py
│   └── config.py               # Environment variable loader
├── tests/
│   ├── __init__.py
│   ├── test_ingest.py
│   └── test_etl.py
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── README.md
└── requirements.txt
```

## BigQuery Schema

**Dataset:** `looker_pipeline` | **Table:** `raw_data`

| Column | Type | Description |
|--------|------|-------------|
| id | STRING | UUID primary key |
| source | STRING | One of: api, webhook, scraper |
| content | STRING | Raw text content |
| title | STRING | Optional title |
| url | STRING | Origin URL if applicable |
| tags | STRING | Comma-separated AI-generated tags |
| ingested_at | TIMESTAMP | When record entered the pipeline |
| processed_at | TIMESTAMP | When ETL/AI tagging completed |
| dag_run_id | STRING | Airflow DAG run identifier |

Partitioned by `ingested_at`; clustered by `source`.

## Airflow DAG Schedule

- **Schedule:** `*/12 * * * *` (every 12 hours)
- **Timeout:** 2 hours per run
- **Retry:** 2 attempts with 10-minute exponential backoff
- **Tasks:** `fetch_gcs_blobs` → `run_etl` → `upsert_bigquery` → `cleanup_gcs_blobs`

---

Built by: KMan | AI-Augmented Engineering Factory