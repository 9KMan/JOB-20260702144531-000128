# Debezium CDC Troubleshooting Guide

## Common Issues and Solutions

### Issue: Connector Fails to Start with "Access Denied" Error

**Symptom:**
```
org.apache.kafka.connect.errors.ConnectException: Error accessing MySQL binary log
```

**Solution:**
1. Verify MySQL user has REPLICATION privileges:
```sql
GRANT REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO 'debezium'@'%';
FLUSH PRIVILEGES;
```

2. Check binlog is enabled:
```sql
SHOW VARIABLES LIKE 'log_bin';
SHOW VARIABLES LIKE 'binlog_format';
```

---

### Issue: PostgreSQL Connector Shows "Logical Decoding Requires WAL Level"

**Symptom:**
```
org.postgresql.util.PSQLException: ERROR: logical decoding requires wal_level = logical
```

**Solution:**
1. Update PostgreSQL container command to set wal_level:
```yaml
command:
  - "wal_level=logical"
  - "max_replication_slots=10"
  - "max_wal_senders=10"
```

2. Recreate the database or restart PostgreSQL.

---

### Issue: Connector Stuck in RUNNING State but No Data Flowing

**Symptom:**
- Connector status shows RUNNING
- No new messages in Kafka topics
- Offset lag is zero or stale

**Diagnosis:**
```bash
# Check connector tasks
curl -s http://localhost:8083/connectors/postgres-source-connector/tasks | jq '.'

# Check last recorded offset
curl -s http://localhost:8083/connectors/postgres-source-connector/status | jq '.tasks[].offset'
```

**Solutions:**
1. Check if replication slot exists:
```sql
SELECT * FROM pg_replication_slots;
```

2. Verify publication exists:
```sql
SELECT * FROM pg_publication;
```

3. If missing, recreate:
```sql
CREATE PUBLICATION dbz_publication FOR ALL TABLES;
SELECT pg_create_logical_replication_slot('debezium_slot', 'pgoutput');
```

---

### Issue: Schema History Topic Not Found

**Symptom:**
```
io.debezium.storage kafka.history.KafkaSchemaHistory: Expected 1 partition
```

**Solution:**
1. Pre-create the schema history topic with 1 partition:
```bash
docker exec kafka-broker kafka-topics \
  --create --topic schema-changes.inventory \
  --partitions 1 --replication-factor 1 \
  --bootstrap-server localhost:9092
```

2. Disable automatic topic creation in production:
```yaml
KAFKA_AUTO_CREATE_TOPICS_ENABLE: 'false'
```

---

### Issue: Out of Memory Errors

**Symptom:**
```
java.lang.OutOfMemoryError: Kafka broker or Connect worker killed
```

**Solution:**
1. Increase Docker memory to 8GB+
2. Add to connect worker:
```json
{
  "worker": {
    "consumer.max.poll.interval.ms": 300000,
    "fetch.max.wait.ms": 500
  }
}
```

---

### Issue: Cannot Connect to Debezium Connect

**Symptom:**
```
java.net.ConnectException: Connection refused (localhost:8083)
```

**Solution:**
1. Verify container is running:
```bash
docker ps | grep kafka-connect
```

2. Check logs:
```bash
docker-compose logs kafka-connect
```

3. Restart if needed:
```bash
docker-compose restart kafka-connect
```

---

### Issue: GTID Mode Error with MySQL

**Symptom:**
```
org.apache.kafka.connect.errors DebeziumException: GTID mode is required
```

**Solution:**
Add to MySQL configuration:
```sql
SET GLOBAL gtid_mode = ON;
SET GLOBAL enforce_gtid_consistency = ON;
```

Or ensure docker-compose has:
```yaml
command:
  - "--gtid-mode=ON"
  - "--enforce-gtid-consistency=ON"
```

---

### Issue: PostgreSQL "Publication Not Found"

**Symptom:**
```
Error:Publication 'dbz_publication' does not exist
```

**Solution:**
1. Connect to PostgreSQL:
```bash
docker exec -it postgres psql -U postgres -d inventory
```

2. Create publication:
```sql
CREATE PUBLICATION dbz_publication FOR ALL TABLES;
```

3. Also ensure the replication slot exists:
```sql
SELECT pg_create_logical_replication_slot('debezium_slot', 'pgoutput');
```

---

## Health Check Commands

### Verify MySQL Binlog
```sql
SHOW MASTER STATUS;
SHOW BINARY LOGS;
```

### Verify PostgreSQL Replication
```sql
SELECT slot_name, plugin, active FROM pg_replication_slots;
SELECT * FROM pg_stat_replication;
```

### Check Kafka Connect Status
```bash
curl -s http://localhost:8083/ | jq '.'
curl -s http://localhost:8083/connectors | jq '.'
```

### Check Topic Offsets
```bash
docker exec kafka-broker kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --describe --group debezium-cluster
```

## Performance Tuning

### For High-Volume Workloads
1. Increase connector tasks:
```json
"tasks.max": "3"
```

2. Adjust poll interval:
```json
"poll.interval.ms": 100
```

3. Add buffering:
```json
"batch.size": 16384
```

### For Low-Latency Requirements
1. Reduce flush interval:
```json
"offset.flush.interval.ms": 100
```

2. Disable schema history:
```json
"include.schema.changes": "false"
```

## Emergency Recovery

### Full Reset
```bash
# 1. Stop connectors
curl -X PUT http://localhost:8083/connectors/*/pause

# 2. Delete connectors
curl -X DELETE http://localhost:8083/connectors/*

# 3. Delete offset topics
docker exec kafka-broker kafka-topics \
  --delete --topic debezium_offsets \
  --bootstrap-server localhost:9092

# 4. Restart Kafka Connect
docker-compose restart kafka-connect

# 5. Re-register connectors
./scripts/register-connectors.sh
```

---

## Support Resources

- Debezium Documentation: https://debezium.io/documentation/
- Debezium Community Slack: https://debezium.io/community/
- Confluent Community Forum: https://community.confluent.io/
