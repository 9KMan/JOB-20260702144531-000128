# Confluent Cloud Deployment Guide

## Overview

This guide covers deploying a Kafka client application to Confluent Cloud Free Tier.

## Confluent Cloud Free Tier Limits

- 1 Kafka cluster
- 100MB/month data transfer
- 3 connectors maximum
- 3 topics (including internal)
- 1 schema registry
- No credit card required

## Setup Steps

### 1. Create Confluent Cloud Account

1. Go to https://confluent.cloud
2. Sign up for free tier
3. Verify email address

### 2. Create a Kafka Cluster

1. In Confluent Cloud dashboard, click "Create cluster"
2. Select "Basic" tier (free)
3. Choose a region close to your users
4. Name your cluster (e.g., "kafka-sprint-cluster")

### 3. Create a Topic

1. Navigate to "Topics" in your cluster
2. Click "Create topic"
3. Name it `events-topic`
4. Set partitions: 3
5. Retention: 7 days (default)

### 4. Generate API Keys

1. Navigate to "API Keys" in your cluster
2. Click "Create key"
3. Choose "Global access" or "Granular access"
4. Save the Key and Secret securely

### 5. Get Schema Registry URL

1. Navigate to "Schema Registry"
2. Copy the endpoint URL
3. Create a Schema Registry API key via "API Keys" page

## Configuration

### Update .env with Confluent Cloud credentials

```bash
# Confluent Cloud
CLOUD_KAFKA_BROKER=your-broker-endpoint:9092
CLOUD_API_KEY=your-api-key
CLOUD_API_SECRET=your-api-secret
CLOUD_SCHEMA_REGISTRY_URL=https://your-instance.ps.confluent.cloud
CLOUD_SCHEMA_REGISTRY_KEY=your-schema-registry-key
CLOUD_SCHEMA_REGISTRY_SECRET=your-schema-registry-secret
CLOUD_TOPIC=events-topic
CLOUD_CONSUMER_GROUP=cloud-consumer-group
CLIENT_TYPE=cloud
```

### Environment Variable Export

```bash
export CLOUD_KAFKA_BROKER=pkc-xxxxx.region.provider.cloud.provider.com:9092
export CLOUD_API_KEY=KIXXXXXX
export CLOUD_API_SECRET=secrettoken
export CLOUD_SCHEMA_REGISTRY_URL=https://psrc-xxxxx.region.provider.confluent.cloud
export CLOUD_SCHEMA_REGISTRY_KEY=SCHEMAXXXXXX
export CLOUD_SCHEMA_REGISTRY_SECRET=secret
export CLIENT_TYPE=cloud
```

## Running the Client

### Test Cloud Producer

```bash
node clients/hybridProducer.js
```

### Test Cloud Consumer

```bash
node clients/cloudConsumer.js
```

## Production Checklist

Before going to production, verify:

- [ ] API keys have minimal required permissions
- [ ] Network policies restrict access
- [ ] Consumer group offsets are properly managed
- [ ] Error handling routes to DLQ
- [ ] Schema Registry has compatibility mode set (BACKWARD)
- [ ] Monitoring and alerting configured
- [ ] Retention policies align with business requirements

## Cost Management

Confluent Cloud Free Tier allows 100MB/month. To avoid overages:

1. Monitor usage in dashboard
2. Set retention to minimum needed (e.g., 24 hours)
3. Use compact topic policy for reference data
4. Delete unused topics promptly
5. Avoid producing debug logs to Kafka

## Troubleshooting

### Connection Refused
- Verify bootstrap server URL is correct
- Check if IP is whitelisted (if using allowlisting)

### Authentication Failed
- Double-check API key and secret
- Ensure key is not expired
- Verify key has correct permissions for the operation

### Schema Registry Error
- Confirm schema compatibility mode is set
- Check Schema Registry API key permissions
- Verify schema subject name matches topic

### Messages Not Appearing
- Check consumer group lag in dashboard
- Verify partition leadership is healthy
- Confirm client is using correct topic name

---

## Debezium CDC Deployment (Week 2)

The Debezium CDC sprint extends the Kafka pipeline with real-time change data capture from MySQL and PostgreSQL.

### Quick Start

```bash
cd kafka-sprint/debezium

# Start all services
docker-compose up -d

# Wait for services to be healthy
docker-compose ps

# Register connectors
./scripts/register-connectors.sh

# Verify CDC events
docker exec -it kafka-broker kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic mysql.inventory.customers \
  --from-beginning
```

### Key Components

| Component | Description |
|-----------|-------------|
| MySQL 8.0 | Source database with binlog CDC |
| PostgreSQL 15 | Source database with logical replication |
| Debezium Connect 2.4 | CDC runtime with MySQL/PostgreSQL connectors |
| Kafka Exporter | Prometheus metrics for Kafka |
| Grafana | CDC monitoring dashboard |

### Documentation Files

| Document | Purpose |
|----------|---------|
| `DEBEZIUM_SPRINT_PLAN.md` | 5-day sprint breakdown |
| `RUNBOOK.md` | Operations guide |
| `TROUBLESHOOTING.md` | Common issues and solutions |
| `SCREENING_QUESTIONS.md` | Technical Q&A for interviews |
