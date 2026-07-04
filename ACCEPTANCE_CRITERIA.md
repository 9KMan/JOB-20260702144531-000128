# Acceptance Criteria — Looker Studio Data Pipeline

## Functional Requirements

- [ ] **FR-01**: FastAPI application starts and binds to configured port (default 8080)
- [ ] **FR-02**: `GET /health` returns HTTP 200 with JSON body containing `status`, `timestamp`, and `service` fields
- [ ] **FR-03**: `POST /ingest/webhook/ingest` accepts a valid `WebhookPayload` and returns HTTP 202 with `record_id` and `queued_at`
- [ ] **FR-04**: `POST /ingest/webhook/ingest` rejects empty `data` field with HTTP 422
- [ ] **FR-05**: `POST /ingest/ingest` accepts valid `IngestRequest` and returns HTTP 202
- [ ] **FR-06**: `GET /status` returns pipeline operational status including `project_id`, `dataset`, and `table`
- [ ] **FR-07**: Webhook endpoints validate incoming JSON and return 400 for malformed payloads
- [ ] **FR-08**: Ingestion endpoint validates `source` field and rejects invalid values
- [ ] **FR-09**: ETL pipeline normalizes raw content fields to `RawEvent` schema
- [ ] **FR-10**: ETL pipeline applies length-based text categorization (short < 100, medium 100–1000, long > 1000 characters)
- [ ] **FR-11**: ETL pipeline deduplicates records by `source_id` + `ingested_at` composite key before insert
- [ ] **FR-12**: BigQuery write mode is append-only with deduplication (no upsert)
- [ ] **FR-13**: `WebhookProcessor` class processes inbound webhook events from the pending queue
- [ ] **FR-14**: `ETLService` class provides `transform()` method that applies the normalization + tagging + deduplication pipeline
- [ ] **FR-15**: `run_pipeline.py` `main()` function executes `WebhookProcessor` followed by `ETLService` end-to-end
- [ ] **FR-16**: All Pydantic models serialize and deserialize without data loss
- [ ] **FR-17**: API responses follow consistent `ErrorResponse` schema for error cases

## Non-Functional Requirements

- [ ] **NFR-01**: All Python source files pass syntax validation (no `SyntaxError`)
- [ ] **NFR-02**: All imports resolve to packages listed in `requirements.txt`
- [ ] **NFR-03**: Pytest test suite runs and all tests pass (`pytest tests/ -v`)
- [ ] **NFR-04**: `run_pipeline.sh` is executable and correctly invokes `run_pipeline.py`
- [ ] **NFR-05**: All environment variables referenced in code have defaults or are marked required in `.env.example`
- [ ] **NFR-06**: BigQuery schema creation script runs without errors against a valid GCP project
- [ ] **NFR-07**: Airflow DAG is valid Python (no import errors, no DAG parsing failures)
- [ ] **NFR-08**: Docker Compose configuration starts both `api` and `airflow-webserver` services successfully
- [ ] **NFR-09**: `SECRET_KEY` is required for webhook signature verification; requests with invalid signatures return 401
- [ ] **NFR-10**: Logging is structured JSON and includes `request_id` for traceability
- [ ] **NFR-11**: API handles concurrent requests without data corruption in the in-memory pending queue
- [ ] **NFR-12**: Cache TTL is respected for metric value caching (120 seconds)
- [ ] **NFR-13**: README contains Business Problem Solved, Architecture diagram, Tech Stack, Getting Started, and Project Structure sections
- [ ] **NFR-14**: SPEC.md exists and documents all major design decisions

## Test Coverage Requirements

- [ ] **TC-01**: `tests/test_api.py` — `test_health_returns_200` passes
- [ ] **TC-02**: `tests/test_api.py` — `test_ingest_webhook_returns_202` passes
- [ ] **TC-03**: `tests/test_api.py` — `test_list_jobs_returns_200` passes
- [ ] **TC-04**: `tests/test_api.py` — `test_get_data_returns_200` passes
- [ ] **TC-05**: `tests/test_bigquery.py` — length categorization transform tests pass
- [ ] **TC-06**: `tests/test_etl.py` — ETLService transform tests pass
- [ ] **TC-07**: `tests/unit/test_bigquery_transformation.py` — all existing transformation pipeline tests pass

## Integration Requirements

- [ ] **IR-01**: `POST /ingest/webhook/ingest` → pending queue → ETL pipeline → BigQuery write completes without errors
- [ ] **IR-02**: BigQuery job-completion webhook triggers cache invalidation
- [ ] **IR-03**: Airflow DAG run success triggers Looker Studio cache invalidation
- [ ] **IR-04**: `run_pipeline.py` can be run standalone and connects to BigQuery using service account credentials