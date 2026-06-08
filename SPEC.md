# Looker Studio Data Pipeline — Specification

## 1. Concept & Vision

An end-to-end automated data pipeline that ingests heterogeneous text data from multiple sources (REST APIs, webhooks, web scrapers) on a 12-hour schedule, processes it through ETL with AI-powered tagging, persists it in Google BigQuery, and surfaces insights via Looker Studio dashboards.

**Feel:** Hands-off, enterprise-grade reliability with observable logging and graceful error handling at every stage.

---

## 2. Technical Architecture

```
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  REST APIs  │   │   Webhooks  │   │   Scrapers  │
└──────┬──────┘   └──────┬──────┘   └──────┬──────┘
       │                 │                 │
       └────────────────┬┴─────────────────┘
                        ▼
              ┌──────────────────┐
              │   FastAPI Ingest │  ← manual trigger / webhook push
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

### Data Flow

1. **Ingest** — FastAPI receives data via REST endpoints or webhook POSTs; raw payloads are written to GCS as JSON blobs.
2. **Schedule** — Airflow DAG fires every 12 hours, reads GCS blobs, and runs the ETL step.
3. **ETL** — Pandas normalises schema, applies AI tagging (keyword + embedding similarity), produces a tidy DataFrame.
4. **Load** — DataFrame is upserted into BigQuery `raw_data` table partitioned by ingestion date.
5. **Visualise** — Looker Studio connects to BigQuery and renders dashboards.

---

## 3. Project Structure

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
│   ├── main.py            # FastAPI app
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── ingest.py       # POST /ingest
│   │   └── health.py       # GET /health
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py      # Pydantic models
│   └── services/
│       ├── __init__.py
│       ├── gcs_writer.py   # GCS blob writing
│       └── bigquery.py     # BigQuery upsert helper
├── dags/
│   ├── __init__.py
│   └── etl_pipeline.py     # Airflow DAG definition
├── lib/
│   ├── __init__.py
│   ├── etl.py              # ETL transformations
│   ├── ai_tagger.py        # AI tagging logic
│   └── config.py           # Env var config loader
└── tests/
    ├── __init__.py
    ├── test_api.py
    ├── test_etl.py
    └── test_ai_tagger.py
```

---

## 4. API Surface

| Method | Path | Description |
|--------|------|-------------|
| POST | `/ingest` | Receive a single text record (JSON body) |
| POST | `/ingest/batch` | Receive multiple records at once |
| POST | `/webhook` | Webhook receiver (GitHub-style event envelope) |
| GET | `/health` | Liveness probe |

---

## 5. BigQuery Schema

**Dataset:** `looker_pipeline`
**Table:** `raw_data`

| Column | Type | Description |
|--------|------|-------------|
| id | STRING | UUID primary key |
| source | STRING | One of: `api`, `webhook`, `scraper` |
| content | STRING | Raw text content |
| title | STRING | Optional title |
| url | STRING | Origin URL if applicable |
| tags | STRING | Comma-separated AI-generated tags |
| ingested_at | TIMESTAMP | When the record entered the pipeline |
| processed_at | TIMESTAMP | When ETL/AI tagging completed |
| dag_run_id | STRING | Airflow DAG run identifier |

Partitioned by `ingested_at`; clustered by `source`.

---

## 6. Airflow DAG Schedule

- **Schedule:** `*/12 * * * *` (every 12 hours)
- **Timeout:** 2 hours
- **Retry:** 2 attempts with 10-minute backoff
- **Tasks:** `fetch_gcs_blobs → run_etl → upsert_bigquery → cleanup_gcs_blobs`

---

## 7. Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| GCP_PROJECT_ID | Yes | — | GCP project ID |
| GCP_BIGQUERY_DATASET | Yes | looker_pipeline | BigQuery dataset name |
| GCP_BIGQUERY_TABLE | Yes | raw_data | BigQuery table name |
| GCP_SERVICE_ACCOUNT_KEY | Yes | ./gcp-key.json | Path to SA key JSON |
| GCS_BUCKET | Yes | — | GCS bucket for blob storage |
| AIRFLOW_HOME | No | ./airflow | Local Airflow home |
| API_PORT | No | 8080 | FastAPI listen port |
| LOG_LEVEL | No | INFO | Logging verbosity |
| AI_TAGGER_MODEL | No | sentence-transformers/all-MiniLM-L6-v2 | HuggingFace model for embeddings |

---

## 8. Error Handling

- API returns HTTP 422 for validation errors, 500 for unexpected failures
- Airflow task failures trigger Slack/email alerts (via Airflow callbacks)
- BigQuery upsert uses `CREATE TABLE IF NOT EXISTS` to be idempotent
- GCS writes are atomic (write to tmp blob, then rename)

---

## 9. Security

- GCP SA key mounted as secret, never committed
- API endpoints behind internal network in production (not exposed publicly)
- Airflow DAG has no `execute` permission for workers outside DAG service account
- All data encrypted at rest in BigQuery and GCS
