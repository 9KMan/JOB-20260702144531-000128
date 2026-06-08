# Kafka Sprint Plan — Week 1 (Days 1–5)

## Objective
Build a production-ready Kafka event streaming pipeline from zero, using Docker Compose for local development and Confluent Cloud Free Tier for managed Kafka experience.

---

## Day 1 — Environment Setup and Kafka Fundamentals

### Goals
- Install Kafka locally (KRaft mode, no Zookeeper)
- Understand topic, producer, consumer, broker concepts
- Run local cluster with Docker Compose

### Tasks
1.1 Install Docker and Docker Compose - 30 min
1.2 Create Kafka Docker Compose cluster (1 broker + Kraft) - 30 min
1.3 Verify broker is up: list topics, describe broker - 15 min
1.4 Create first topic demo-topic with 3 partitions - 10 min
1.5 Write and run a Node.js or Python producer script - 30 min
1.6 Write and run a consumer group with 2 consumers - 30 min
1.7 Verify offset tracking and message replay - 15 min

### Day 1 Files
kafka-sprint/
  docker-compose.local.yml
  scripts/
    create-topics.sh
    producer.js
    consumer.js

---

## Day 2 — Confluent Cloud Setup + Hybrid Producer/Consumer

### Goals
- Set up Confluent Cloud Free Tier account
- Create a cluster, topic, and get API keys
- Build a producer that writes to both local and cloud

### Tasks
2.1 Sign up for Confluent Cloud (free tier) - 15 min
2.2 Create a cloud cluster and topic events-topic - 15 min
2.3 Generate Cloud API key and secret - 10 min
2.4 Create hybrid client config (env: LOCAL / CLOUD) - 30 min
2.5 Write a multi-destination producer (local + cloud) - 60 min
2.6 Write a consumer that reads from Confluent Cloud - 45 min
2.7 Test cross-environment message flow - 30 min

### Day 2 Files
kafka-sprint/
  config/
    local.config.js
    cloud.config.js
  clients/
    hybridProducer.js
    cloudConsumer.js
  .env.example

---

## Day 3 — Schema Registry + Data Serialization

### Goals
- Add Schema Registry to Docker Compose (local)
- Define Avro or JSON Schema for events
- Implement typed produce and consume with schema validation

### Tasks
3.1 Add Schema Registry to docker-compose.local.yml - 30 min
3.2 Register OrderEvent schema (JSON Schema) - 20 min
3.3 Write schema-validated producer - 45 min
3.4 Write schema-validated consumer - 45 min
3.5 Test schema evolution (add optional field) - 30 min
3.6 Compare serialization: JSON vs Avro vs Protobuf - 45 min

### Day 3 Files
kafka-sprint/
  schemas/
    order-event.schema.json
  clients/
    schemaRegistryClient.js
    validatedProducer.js
    validatedConsumer.js

---

## Day 4 — Stream Processing and Error Handling

### Goals
- Build a Kafka Streams or KSQL processor
- Implement dead-letter queue (DLQ) for failed messages
- Add consumer group rebalancing handling

### Tasks
4.1 Design event processing topology - 30 min
4.2 Implement stream processor (transform and aggregate) - 60 min
4.3 Set up DLQ topic events.DLQ - 20 min
4.4 Add retry logic with exponential backoff - 30 min
4.5 Implement idempotent consumer - 30 min
4.6 Test rebalancing (add or remove consumer mid-run) - 30 min
4.7 Add health check endpoint to consumers - 20 min

### Day 4 Files
kafka-sprint/
  processors/
    streamProcessor.js
    dlqHandler.js
  services/
    retryService.js

---

## Day 5 — Production Hardening and Observability

### Goals
- Add Prometheus metrics export for Kafka
- Configure consumer lag monitoring
- Write integration tests
- Create deployment runbook

### Tasks
5.1 Add Kafka Exporter + Prometheus to docker-compose - 30 min
5.2 Configure Grafana dashboards - 45 min
5.3 Add Prometheus metrics to consumer clients - 30 min
5.4 Write integration test suite (produce, consume, verify) - 60 min
5.5 Document local dev setup for new engineers - 30 min
5.6 Create deployment runbook (Confluent Cloud) - 30 min
5.7 Create docker-compose.prod.yml for cloud-connected mode - 30 min

### Day 5 Files
kafka-sprint/
  docker-compose.prod.yml
  monitoring/
    prometheus.yml
    grafana-dashboard.json
  tests/
    integration.test.js
  RUNBOOK.md
  DEPLOYMENT.md

---

## End-of-Week Deliverables

| # | Deliverable | Location |
|---|-------------|----------|
| 1 | Docker Compose local Kafka cluster | docker-compose.local.yml |
| 2 | Confluent Cloud connected producer/consumer | clients/hybridProducer.js |
| 3 | Schema-validated event pipeline | schemas/ + clients/validatedProducer.js |
| 4 | Stream processor with DLQ | processors/ |
| 5 | Prometheus + Grafana observability | monitoring/ |
| 6 | Integration test suite | tests/integration.test.js |
| 7 | Local dev setup runbook | RUNBOOK.md |
| 8 | Confluent Cloud deployment guide | DEPLOYMENT.md |

---

## Tech Stack Summary

| Component | Technology |
|-----------|------------|
| Local Kafka | Kafka 3.x (KRaft), Docker Compose |
| Managed Kafka | Confluent Cloud Free Tier |
| Language | Node.js 20+ (KafkaJS) or Python (confluent-kafka) |
| Schema Registry | Confluent Schema Registry (local Docker) |
| Serialization | JSON Schema, Avro |
| Observability | Prometheus + Grafana + Kafka Exporter |
| Testing | Jest or Mocha |

---

## Prerequisites (Pre-Sprint)

- Docker Desktop 4.x+
- Node.js 20+ or Python 3.11+
- Confluent Cloud account (free tier - credit card not required)
- 4GB+ RAM allocated to Docker

---

## Tips

- KRaft over Zookeeper: Kafka 3.5+ no longer needs Zookeeper. Use bootstrap-server exclusively.
- Confluent Cloud Free Tier Limits: 1 cluster, 100MB per month, 3 connectors. Do not exceed.
- Consumer Group Offsets: Use earliest offset reset policy for dev to avoid no offset errors.
- Schema Evolution: Always mark new fields as optional to maintain backward compatibility.
