# Debezium CDC Sprint Plan — Week 2 (Days 6–10)

## Objective

Extend the Week 1 Kafka pipeline with Change Data Capture (CDC) using Debezium to capture real-time database changes from MySQL and PostgreSQL into Kafka topics.

---

## Day 6 — Debezium Fundamentals and MySQL Setup

### Goals
- Understand CDC concepts and Debezium architecture
- Set up MySQL with binlog enabled for CDC
- Deploy Debezium Connect with MySQL source connector

### Tasks
6.1 Install MySQL container with binlog enabled - 30 min
6.2 Create sample database and tables for CDC - 20 min
6.3 Deploy Debezium Connect container - 30 min
6.4 Register MySQL source connector - 30 min
6.5 Verify CDC events flow to Kafka topic - 30 min

### Day 6 Files
debezium/
  docker-compose.yml
  config/
    mysql-source-connector.json
  scripts/
    setup-mysql.sh
    register-connectors.sh

---

## Day 7 — PostgreSQL CDC and Connector Configuration

### Goals
- Set up PostgreSQL with logical replication
- Configure Debezium PostgreSQL connector
- Handle schema evolution and topic routing

### Tasks
7.1 Set up PostgreSQL with logical replication - 30 min
7.2 Create publication and replication slot - 20 min
7.3 Register PostgreSQL source connector - 30 min
7.4 Configure topic routing transforms - 30 min
7.5 Test CDC with DML operations - 45 min

### Day 7 Files
debezium/
  config/
    postgres-source-connector.json
    topic-routing.json
  scripts/
    setup-postgres.sh

---

## Day 8 — Debezium SMT and Data Transformation

### Goals
- Configure Single Message Transforms (SMT)
- Implement outbox pattern for reliable events
- Add data masking for sensitive fields

### Tasks
8.1 Configure ExtractNewRecordState SMT - 30 min
8.2 Implement outbox table pattern - 60 min
8.3 Add field masking transform - 30 min
8.4 Configure topic creation rules - 30 min
8.5 Test schema evolution with SMT - 30 min

### Day 8 Files
debezium/
  config/
    outbox-connector.json
    masking-transform.json
  scripts/
    outbox-setup.sql

---

## Day 9 — Error Handling, Monitoring and Production Setup

### Goals
- Configure dead letter queue for failed records
- Add Prometheus metrics for Debezium
- Set up alerts for connector health
- Production-ready configuration review

### Tasks
9.1 Configure error handling with DLQ - 30 min
9.2 Add Debezium metrics to Prometheus - 30 min
9.3 Create Grafana dashboard for CDC - 45 min
9.4 Implement rebalancing handling - 30 min
9.5 Review production configuration checklist - 30 min

### Day 9 Files
debezium/
  config/
    dlq-connector.json
    metrics-config.json
  monitoring/
    debezium-dashboard.json

---

## Day 10 — Integration Testing and Documentation

### Goals
- End-to-end integration tests
- Complete runbook and troubleshooting guide
- Performance benchmarking

### Tasks
10.1 Create CDC integration tests - 60 min
10.2 Performance benchmark (1000 ops/sec) - 45 min
10.3 Write troubleshooting runbook - 45 min
10.4 Document common issues and fixes - 30 min
10.5 Sprint retrospective and next steps - 30 min

### Day 10 Files
debezium/
  tests/
    cdc-integration.test.js
  RUNBOOK.md
  TROUBLESHOOTING.md

---

## Two-Week Sprint Deliverables

| # | Deliverable | Location |
|---|-------------|----------|
| 1 | Debezium MySQL CDC pipeline | debezium/config/mysql-source-connector.json |
| 2 | Debezium PostgreSQL CDC pipeline | debezium/config/postgres-source-connector.json |
| 3 | Outbox pattern implementation | debezium/config/outbox-connector.json |
| 4 | Data masking transforms | debezium/config/masking-transform.json |
| 5 | Monitoring dashboard | debezium/monitoring/debezium-dashboard.json |
| 6 | CDC integration tests | debezium/tests/cdc-integration.test.js |
| 7 | Debezium runbook | debezium/RUNBOOK.md |
| 8 | Troubleshooting guide | debezium/TROUBLESHOOTING.md |

---

## Debezium Architecture Overview

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│   MySQL     │────▶│ Debezium Connect │────▶│   Kafka     │
│  (binlog)   │     │  (Source Conn.)  │     │   Broker    │
└─────────────┘     └──────────────────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    │ Prometheus  │
                    │  Metrics    │
                    └─────────────┘
```

### Key Components
- **Debezium Connect**: Runtime for running connectors
- **MySQL Source Connector**: Captures row-level changes via binlog
- **PostgreSQL Source Connector**: Uses logical replication slots
- **SMT (Single Message Transform)**: Transforms CDC events

---

## Tech Stack for Week 2

| Component | Technology |
|-----------|------------|
| CDC Engine | Debezium 2.x |
| Source Databases | MySQL 8.0, PostgreSQL 15 |
| Message Format | JSON (with Debezium envelope) |
| Transforms | Debezium SMT |
| Monitoring | Prometheus + Grafana |
| Testing | Jest |

---

## Prerequisites for Week 2

- Week 1 Kafka cluster running
- Docker Compose knowledge
- Basic SQL knowledge
- 8GB+ RAM for additional containers

## Tips

- Always enable GTID mode in MySQL for easier connector recovery
- Use logical replication for PostgreSQL (wal_level = logical)
- Monitor connector offset lag to detect issues early
- Set appropriate snapshot.mode based on data freshness needs
