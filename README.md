# Looker Studio Data Pipeline

> Automated text ingestion, ETL with AI tagging, BigQuery storage, and Looker Studio visualisation — every 12 hours.

---

## Business Problem Solved

Manually aggregating text data from REST APIs, webhook feeds, and web scraping tools is a repetitive, error-prone task that consumes hours of analyst time every week. Data arrives in inconsistent schemas, making downstream reporting brittle and hard to trust.

This project eliminates that toil by providing a fully automated pipeline: sources push or are polled on a 12-hour schedule; a FastAPI ingestion layer accepts and validates records; an Airflow DAG orchestrates ETL with AI-powered tagging; data lands in BigQuery ready for Looker Studio dashboards that business users can self-serve without engineering involvement.

The concrete outcome: analysts receive a live, single-source-of-truth dashboard refreshed twice daily, and the engineering team stops writing one-off export scripts every time a new data source is added.

---

## Architecture Overview

```
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  REST APIs  │   │   Webhooks  │   │   Scrapers  │
└──────┬──────┘   └──────┬──────┘   └──────┬──────┘
       │                 │                 │
       └────────────────┬┴─────────────────┘
                        ▼
              ┌──────────────────┐
              │   FastAPI Ingest │
              │   (Port 8080)    │
              └────────┬─────────┘
                       ▼
              ┌──────────────────┐
              │  Airflow DAG     │  ← scheduled every 12 h
              │  (ETL + AI Tag)  │
              └────────┬─────────┘
                       ▼
              ┌──────────────────┐
              │   BigQuery        │
              │   (raw_data table)│
              └────────┬─────────┘
                       ▼
              ┌──────────────────┐
              │  Looker Studio   │
              │    Dashboard      │
              └──────────────────┘
```

**Data flow:** Sources → FastAPI (validate & stage to GCS) → Airflow DAG (ETL + AI tag) → BigQuery → Looker Studio.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Ingestion API | FastAPI 0.111 / Uvicorn |
| Orchestration | Apache Airflow 2.9 |
| Cloud Storage | Google Cloud Storage |
| Data Warehouse | Google BigQuery |
| Visualisation | Looker Studio |
| Language | Python 3.11 |
| Container | Docker / Docker Compose |
| Auth | GCP Service Account JSON |

---

## Getting Started

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- GCP project with BigQuery and GCS APIs enabled
- Service Account key with roles: `BigQuery Data Editor`, `Storage Object Creator`

### 1 — Clone & install dependencies

```bash
git clone https://github.com/your-org/looker-studio-pipeline.git
cd looker-studio-pipeline

python3 -m venv .venv
source .venv/bin/activate          # Linux/macOS
# .\.venv\Scripts\Activate.ps1     # Windows

pip install -r requirements.txt
```

### 2 — Configure environment

```bash
cp .env.example .env
# Edit .env with your values (see below)
```

Required `.env` variables:

| Variable | Description |
|----------|-------------|
| `GCP_PROJECT_ID` | Your GCP project ID |
| `GCP_BIGQUERY_DATASET` | BigQuery dataset name |
| `GCP_BIGQUERY_TABLE` | Target table name |
| `GCP_SERVICE_ACCOUNT_KEY` | Path to the SA key JSON file |
| `GCS_BUCKET` | GCS bucket for staging blobs |

### 3 — Authenticate with GCP

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/gcp-key.json"
```

Or rely on the `GCP_SERVICE_ACCOUNT_KEY` env var — the application converts it automatically.

### 4 — Run the API

```bash
uvicorn api.main:app --reload --port 8080
```

Verify:
```bash
curl http://localhost:8080/health
```

### 5 — Run Airflow (with Docker Compose)

```bash
docker-compose up -d airflow-init   # one-time init
docker-compose up -d               # starts API + Airflow
```

### 6 — Open Looker Studio

Connect Looker Studio to your BigQuery table using the service account or a read-only SA and build your first chart.

---

## API Overview

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/ingest` | Ingest a single record |
| `POST` | `/ingest/batch` | Ingest up to 1 000 records in one call |
| `POST` | `/webhook` | Receive webhook events (GitHub-style envelope) |
| `GET` | `/health` | Liveness probe |

### Example: Single record

```bash
curl -X POST http://localhost:8080/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "source": "api",
    "content": "Q3 earnings call highlights: revenue up 18% YoY.",
    "title": "Earnings Q3 2024",
    "url": "https://example.com/earnings/q3-2024"
  }'
```

### Example: Batch

```bash
curl -X POST http://localhost:8080/ingest/batch \
  -H "Content-Type: application/json" \
  -d '{"records": [
    {"source": "api", "content": "First record"},
    {"source": "scraper", "content": "Second record", "url": "https://ex.com/2"}
  ]}'
```

---

## Project Structure

```
looker-studio-pipeline/
├── README.md
├── SPEC.md
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── api/
│   ├── __init__.py
│   ├── main.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── ingest.py
│   │   └── health.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py
│   └── services/
│       ├── __init__.py
│       ├── gcs_writer.py
│       └── bigquery.py
├── dags/
│   ├── __init__.py
│   └── etl_pipeline.py
├── lib/
│   ├── __init__.py
│   ├── etl.py
│   ├── ai_tagger.py
│   └── config.py
└── tests/
    ├── __init__.py
    ├── test_api.py
    ├── test_etl.py
    └── test_ai_tagger.py
```

---

## BigQuery Table Schema

**Dataset:** `looker_pipeline`
**Table:** `raw_data` (partitioned by `ingested_at`, clustered by `source`)

| Column | Type | Description |
|--------|------|-------------|
| `id` | STRING | UUID primary key |
| `source` | STRING | `api`, `webhook`, or `scraper` |
| `content` | STRING | Raw text |
| `title` | STRING | Optional title |
| `url` | STRING | Origin URL |
| `tags` | STRING | Comma-separated AI tags |
| `ingested_at` | TIMESTAMP | When FastAPI received the record |
| `processed_at` | TIMESTAMP | When ETL/AI tagging finished |
| `dag_run_id` | STRING | Airflow run identifier |

---

## Airflow DAG

The DAG runs every **12 hours** (`*/12 * * * *`) and executes:

```
fetch_gcs_blobs  →  run_etl  →  upsert_bigquery  →  cleanup_gcs_blobs
```

On failure: 2 retries with 10-minute exponential backoff. Success/failure alerts via Airflow callbacks (configure `alert_email` in the DAG).

---

Built by: **KMan | AI-Augmented Engineering Factory**
