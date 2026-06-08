# Kafka Local Development Runbook

## Prerequisites

- Docker Desktop 4.x+ or Docker Engine 20.10+
- Node.js 20+ or Python 3.11+
- 4GB+ RAM allocated to Docker

## Quick Start

### 1. Start the Kafka Cluster

```bash
cd kafka-sprint
docker-compose -f docker-compose.local.yml up -d
```

### 2. Verify Services

```bash
docker exec kafka-broker kafka-broker-api-versions --bootstrap-server localhost:9092
curl http://localhost:8081/subjects
open http://localhost:8090
```

### 3. Create Topics

```bash
chmod +x scripts/create-topics.sh
./scripts/create-topics.sh
```

### 4. Install Dependencies

```bash
npm init -y
npm install kafkajs @confluentinc/schema-registry-js
```

### 5. Run Producer and Consumer

```bash
node scripts/producer.js demo-topic 10
node scripts/consumer.js demo-topic
```

## Common Commands

### List Topics
```bash
docker exec kafka-broker kafka-topics --bootstrap-server localhost:9092 --list
```

### Describe Topic
```bash
docker exec kafka-broker kafka-topics --bootstrap-server localhost:9092 --describe --topic demo-topic
```

### Reset Consumer Group Offset
```bash
docker exec kafka-broker kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --group demo-consumer-group \
  --reset-offsets --to-earliest \
  --topic demo-topic \
  --execute
```

### Delete Topic
```bash
docker exec kafka-broker kafka-topics --bootstrap-server localhost:9092 --delete --topic demo-topic
```

## Troubleshooting

### Broker wont start
Check if port 9092 is already in use:
```bash
lsof -i :9092
```

### Consumer not receiving messages
- Verify consumer group is subscribed
- Check if messages were produced to correct topic
- Verify offset reset policy using --from-beginning

### Schema Registry errors
- Ensure schema-registry container is healthy
- Check SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS points to kafka:9092

## Project Structure

```
kafka-sprint/
  docker-compose.local.yml   Local Kafka + Schema Registry
  scripts/                    Producer/consumer scripts
  config/                     Client configurations
  clients/                    Hybrid and validated clients
  schemas/                    JSON/Avro schemas
  processors/                 Stream processor and DLQ
  services/                   Retry service
  monitoring/                Prometheus/Grafana configs
  tests/                      Integration tests
```

## Environment Variables

Create .env from .env.example:
```bash
cp .env.example .env
```

| Variable | Description | Default |
|----------|-------------|---------|
| KAFKA_BROKER | Kafka broker address | localhost:9092 |
| SCHEMA_REGISTRY_URL | Schema Registry URL | http://localhost:8081 |
| CLIENT_TYPE | local/cloud/both | local |
| CONSUMER_GROUP_ID | Consumer group ID | demo-consumer-group |
| LOCAL_TOPIC | Local topic name | demo-topic |
