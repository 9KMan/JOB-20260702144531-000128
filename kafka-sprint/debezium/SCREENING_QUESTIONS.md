# Debezium CDC Technical Screening - Question Answers

## Section 1: Debezium Fundamentals

### Q1: What is Debezium and how does it differ from other CDC tools?

**Answer:**
Debezium is an open-source distributed platform for change data capture (CDC). It builds on Apache Kafka to provide durable and reliable data streaming from databases into other systems.

**Key differences from other CDC tools:**
- **Debezium vs. Custom Triggers**: Debezium uses database native features (binlog for MySQL, WAL for PostgreSQL) rather than application-level triggers, causing zero performance overhead on source databases
- **Debezium vs. ETL Tools**: Debezium captures events continuously in real-time rather than batch-based, enabling sub-second latency
- **Debezium vs. Kafka Connect JDBC Source**: Debezium captures actual row-level changes with before/after states; JDBC source only polls at intervals and misses deletions

**Architecture:**
```
MySQL/PostgreSQL → Debezium Connect → Kafka Topic → Downstream Consumer
     (binlog/WAL)      (Connector)       (Events)       (Sinks)
```

---

### Q2: Explain the Debezium event envelope structure.

**Answer:**
Each Debezium event contains:

```json
{
  "schema": { },           // Schema of the payload (optional)
  "payload": {
    "before": { },         // State before change (null for INSERT)
    "after": { },          // State after change (null for DELETE)
    "source": {            // Metadata about the source
      "version": "2.4.0",
      "connector": "mysql",
      "name": "mysql",
      "ts_ms": 1234567890000,
      "snapshot": false,
      "db": "inventory",
      "table": "customers",
      "server_id": 1,
      "gtid": "...",
      "file": "mysql-bin.000001",
      "pos": 1234,
      "row": 0,
      "thread": 5
    },
    "op": "c|r|u|d",      // Operation: create/read/update/delete
    "ts_ms": 1234567890000 // Timestamp in milliseconds
  }
}
```

**Operation codes:**
- `c` = CREATE (INSERT)
- `r` = READ (snapshot reads)
- `u` = UPDATE
- `d` = DELETE

---

## Section 2: Database Configuration

### Q3: What configuration is required to enable CDC on MySQL?

**Answer:**

**1. Enable Binary Logging:**
```sql
log-bin = mysql-bin
binlog-format = ROW
binlog-row-image = FULL
server-id = 1
```

**2. Create Debezium User:**
```sql
CREATE USER 'debezium'@'%' IDENTIFIED BY 'password';
GRANT SELECT, RELOAD, SHOW DATABASES, REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO 'debezium';
GRANT LOCK TABLES ON *.* TO 'debezium';  -- For snapshots
FLUSH PRIVILEGES;
```

**3. Enable GTID Mode (recommended):**
```sql
gtid-mode = ON
enforce-gtid-consistency = ON
```

**4. Docker Compose Configuration:**
```yaml
command:
  - "--binlog-format=ROW"
  - "--binlog-row-image=FULL"
  - "--server-id=1"
  - "--log-bin=mysql-bin"
  - "--gtid-mode=ON"
  - "--enforce-gtid-consistency=ON"
```

---

### Q4: How do you enable CDC on PostgreSQL?

**Answer:**

**1. Set WAL Level to Logical:**
```bash
wal_level = logical
max_replication_slots = 10
max_wal_senders = 10
```

**2. Create Replication Slot:**
```sql
SELECT pg_create_logical_replication_slot('debezium_slot', 'pgoutput');
```

**3. Create Publication:**
```sql
CREATE PUBLICATION dbz_publication FOR ALL TABLES;
```

**4. Docker Compose Configuration:**
```yaml
command:
  - "wal_level=logical"
  - "max_replication_slots=10"
  - "max_wal_senders=10"
```

---

## Section 3: Connector Configuration

### Q5: Explain the key Debezium connector configuration properties.

**Answer:**

| Property | Description | Example |
|----------|-------------|---------|
| `database.hostname` | Source database host | `mysql` |
| `database.port` | Database port | `3306` |
| `database.user` | CDC user | `debezium` |
| `database.password` | CDC user password | `dbz123` |
| `database.server.id` | Unique server ID | `1` |
| `topic.prefix` | Prefix for Kafka topics | `mysql` |
| `database.include.list` | Databases to capture | `inventory` |
| `table.include.list` | Tables to capture | `inventory.orders` |
| `plugin.name` | Postgres logical decoder | `pgoutput` |
| `snapshot.mode` | Initial snapshot strategy | `initial` |
| `publication.name` | Postgres publication | `dbz_publication` |
| `slot.name` | Postgres replication slot | `debezium_slot` |

**Snapshot Modes:**
- `initial` - Captures full state on first start, then continues reading binlog
- `schema_only` - Skips snapshot, captures only new changes
- `when_needed` - Snapshot only when needed (offset lost, etc.)
- `never` - Never take snapshot, assume initial data exists

---

### Q6: What is the purpose of the topic.prefix property?

**Answer:**
The `topic.prefix` creates a namespace for all topics produced by a connector. For example, with `topic.prefix=mysql`:

- MySQL `inventory.customers` table → Kafka topic `mysql.inventory.customers`
- MySQL `inventory.orders` table → Kafka topic `mysql.inventory.orders`

**Important constraints:**
- Must be unique per connector (multiple connectors can't share same prefix)
- Should use database server name or logical server identifier
- Results in topic names like: `{prefix}.{database}.{table}`

---

## Section 4: Transforms and SMT

### Q7: What are Debezium SMTs and when would you use them?

**Answer:**
Single Message Transforms (SMTs) are Kafka Connect transformations applied to records as they pass through the connector.

**Common Debezium SMTs:**

1. **EventRouter** - Routes events to different topics based on field values
   ```json
   "transforms": "router"
   "transforms.router.type": "io.debezium.transforms.outbox.EventRouter"
   ```

2. **ExtractNewRecordState** - Flattens Debezium envelope to just the `after` state
   ```json
   "transforms": "extract"
   "transforms.extract.type": "io.debezium.transforms.ExtractNewRecordState"
   ```

3. **MaskField** - Masks sensitive field values
   ```json
   "transforms": "mask"
   "transforms.mask.type": "org.apache.kafka.connect.transforms.MaskField$Value"
   "transforms.mask.fields": "ssn,credit_card"
   "transforms.mask.replacement": "****"
   ```

4. **RegexRouter** - Modifies topic names with regex
   ```json
   "transforms": "rename"
   "transforms.rename.type": "org.apache.kafka.connect.transforms.RegexRouter"
   "transforms.rename.regex": "(.*)"
   "transforms.rename.replacement": "$1-events"
   ```

---

### Q8: Explain the Outbox Pattern and why it's used.

**Answer:**
The Outbox Pattern is a reliable way to send domain events alongside database changes.

**Problem it solves:**
Without outbox, you need to:
1. Update database record
2. Publish event to message broker

This creates a distributed transaction problem - what if step 2 fails?

**Outbox Solution:**
```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Service   │─────▶│  Database   │─────▶│   Outbox    │
│   Updates   │      │  (1 tx)     │      │   Table     │
└─────────────┘      └─────────────┘      └──────┬──────┘
                                                 │
                                          Debezium CDC
                                                 │
                                                 ▼
                                        ┌─────────────┐
                                        │   Kafka     │
                                        │   Topic     │
                                        └─────────────┘
```

**Setup:**
1. Application writes to both the entity table AND outbox table in a single transaction
2. Debezium captures the outbox table changes
3. A separate process reads outbox and publishes to Kafka
4. EventRouter SMT routes outbox events to proper topic

---

## Section 5: Error Handling

### Q9: How do you handle errors and failures in Debezium pipelines?

**Answer:**

**1. Dead Letter Queue (DLQ) Pattern:**
```json
"error.tolerance": "all",
"errors.deadletter.queue.topic.name": "errors.DLQ",
"errors.deadletter.producer.bootstrap.servers": "kafka:9092",
"errors.deadletter.context.headers.enable": "true"
```

**2. Retry Configuration:**
```json
"errors.retry.timeout": 3600000,
"errors.retry.delay.max.ms": 300000
```

**3. Idempotent Consumers:**
- Store processed event IDs to detect duplicates
- Use the Debezium `source.ts_ms` + `source.file` + `source.pos` as idempotency key

**4. Schema Evolution Handling:**
- Set compatibility mode in Schema Registry: `BACKWARD`
- Use optional fields for new columns
- Never delete required fields

**5. Offset Management:**
- Monitor consumer group lag
- Ensure offset storage topic has adequate retention:
  ```bash
  kafka-topics --alter --topic debezium_offsets --config retention.ms=604800000
  ```

---

### Q10: What monitoring would you set up for a Debezium CDC pipeline?

**Answer:**

**Key Metrics to Monitor:**

1. **Connector Health:**
   - `kafka_connect_connector_state` - Should always be RUNNING
   - `kafka_connect_connector_tasks_total` - Task count

2. **Data Flow:**
   - `kafka_connect_connect_worker_metrics_messages_consumed_total`
   - `kafka_connect_connect_worker_metrics_offset_lag_consumer`

3. **Latency:**
   - `kafka_connect_connect_worker_metrics_fetch_rate_consumer`
   - Source timestamp vs. processing timestamp delta

4. **Errors:**
   - `kafka_connect_connect_worker_metrics_failed_record_total`
   - `kafka_connect_connect_worker_metrics_deadletter_queue_produced_total`

**Prometheus Alert Rules:**
```yaml
groups:
  - name: debezium
    rules:
      - alert: ConnectorDown
        expr: kafka_connect_connector_state != 1
        for: 1m
        labels:
          severity: critical
      - alert: OffsetLagHigh
        expr: kafka_connect_connect_worker_metrics_task_offset_lag_consumer > 10000
        for: 5m
```

**Grafana Dashboard Panels:**
- Connector status (stat panel)
- Messages consumed rate (graph)
- Offset lag over time (graph)
- Dead letter queue size (graph)
- Schema history events (graph)

---

## Section 6: Production Considerations

### Q11: What production hardening would you apply to Debezium?

**Answer:**

**1. High Availability:**
```json
"tasks.max": "3"  // Run multiple parallel tasks
```
For MySQL: Ensure `server_id` is unique per connector instance.

**2. Schema Registry Hardening:**
```json
SCHEMA_REGISTRY_COMPATIBILITY: "BACKWARD"
SCHEMA_REGISTRY_AUTH_CACHE_TTL: 3600000
```

**3. Kafka Topic Configuration:**
```bash
# Internal topics should have:
--config cleanup.policy=compact  # For offset/topic config topics
--config retention.ms=604800000  # 7 days for offset topic

# Data topics should have:
--config cleanup.policy=delete
--config retention.ms=86400000   # 1 day default
```

**4. Security:**
```json
"database.ssl.mode": "required",  // For MySQL SSL
"database.ssl": true              // For PostgreSQL SSL
```

**5. Resource Limits:**
```yaml
resources:
  limits:
    memory: 2G
    cpus: 1.0
  reservations:
    memory: 1G
```

**6. Backoff Configuration:**
```json
"retry.backoff.initial.ms": 1000
"retry.backoff.max.ms": 60000
"retry.backoff.max.delay.ms": 120000
```

---

### Q12: How would you handle schema evolution with Debezium?

**Answer:**

**Backward Compatibility (Recommended):**
```json
// In Schema Registry
SCHEMA_REGISTRY_COMPATIBILITY: BACKWARD
```

**Evolution Rules:**
1. **Adding Fields**: Always add as optional with default value
   ```json
   {
     "type": "object",
     "properties": {
       "existing_field": { "type": "string" },
       "new_field": { "type": "string", "default": "" }
     }
   }
   ```

2. **Removing Fields**: Only remove optional fields; never remove required fields

3. **Renaming Fields**: Add new field, deprecate old, migrate data, then remove

4. **Type Changes**: Use compatible types (int → long, float → double)

**Schema Evolution in Connector:**
```json
"schema.history.internal.kafka.topic": "schema-changes.inventory",
"include.schema.changes": "true"
```

**Best Practices:**
- Always test schema evolution in dev environment first
- Use optional fields for new columns
- Never rename fields directly - use deprecated alias pattern
- Monitor Schema Registry compatibility violations

---

### Q13: What's the difference between snapshot modes and when would you use each?

**Answer:**

| Mode | Behavior | Use Case |
|------|----------|----------|
| `initial` | Full snapshot on first run, then stream | Fresh installation - complete data copy |
| `schema_only` | Never snapshot, only stream new changes | Data already captured, only want changes |
| `when_needed` | Snapshot only when connector has no valid offset | Recovery after failure |
| `never` | Never snapshot | Table is empty or already captured |
| `schema_only_recovery` | Snapshot schema only for recovery | Only schema needed for new consumers |

**Choosing Snapshot Mode:**

```json
// First-time setup - need all historical data
"snapshot.mode": "initial"

// Production - connector has been running, need minimal downtime restart
"snapshot.mode": "schema_only"

// After connector offset lost (corrupted offset topic)
/"snapshot.mode": "when_needed"
```

**Snapshot Locking:**
```json
"snapshot.locking.mode": "minimal"  // Default - holds lock briefly
"snapshot.locking.mode": "none"     // No lock - concurrent DDL may fail
```

---

## Section 7: Integration Scenarios

### Q14: How would you integrate Debezium with an existing data warehouse?

**Answer:**

**Architecture:**
```
MySQL/PostgreSQL → Debezium → Kafka → Kafka Connect JDBC Sink → Data Warehouse
                              ↓
                         Schema Registry
                              ↓
                         S3 / Iceberg / BigQuery
```

**Design:**
1. **Full Refresh Table**: Capture all changes and upsert to warehouse table
2. **Change Log Table**: Store incremental changes with CDC metadata for audit

**JDBC Sink Configuration:**
```json
{
  "name": "warehouse-sink",
  "config": {
    "connector.class": "io.confluent.connect.jdbc.JdbcSinkConnector",
    "topics": "mysql.inventory.customers",
    "connection.url": "jdbc:postgresql://warehouse:5432/analytics",
    "insert.mode": "upsert",
    "pk.mode": "record_key",
    "pk.fields": "id",
    "auto.create": "true",
    "transforms": "unwrap,route",
    "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState",
    "transforms.route.type": "org.apache.kafka.connect.transforms.RegexRouter",
    "transforms.route.regex": "mysql.inventory.(.*)",
    "transforms.route.replacement": "wh_$1"
  }
}
```

---

### Q15: How do you ensure exactly-once semantics with Debezium?

**Answer:**

**Understanding Debezium Guarantees:**
Debezium provides **at-least-once** delivery by default. Exactly-once requires additional handling.

**Achieving Exactly-Once:**

1. **Idempotent Sinks:**
   ```javascript
   // Track processed transaction IDs
   const processedTxIds = new Set();
   
   async function processEvent(event) {
     const txId = `${event.source.ts_ms}-${event.source.file}-${event.source.pos}`;
     if (processedTxIds.has(txId)) return; // Skip duplicate
     
     await sink.process(event.payload.after);
     processedTxIds.add(txId);
   }
   ```

2. **Transactional Outbox Pattern:**
   - Write to entity table + outbox table in single DB transaction
   - Outbox ensures exactly-once semantics within the source

3. **Database Transactions + Debezium:**
   - Source DB must use row-level binlog replication
   - This is inherently transactional - each row change is atomic

4. **Sink Exactly-Once (Kafka Transactions):**
   ```json
   // Enable exactly-once in Kafka Connect
   "enable.idempotence": true,
   "acks": "all",
   "retries": 2147483647
   ```

5. **Two-Phase Commit Pattern:**
   For critical systems, implement:
   - Write to staging table
   - Commit to main table
   - Debezium captures both atomically
   - Sink processes with deduplication

**Best Practice:** Design sinks to be idempotent and rely on Debezium's at-least-once with sink-side deduplication.

---

## Section 8: Performance and Scaling

### Q16: How do you scale Debezium connectors?

**Answer:**

**Horizontal Scaling (tasks.max):**
```json
"tasks.max": "3"
```
Each task processes a subset of tables/partitions. MySQL connectors can scale to multiple tasks for different tables.

**Vertical Scaling:**
```yaml
resources:
  limits:
    memory: 4G
    cpus: 2.0
```

**Partition-Level Parallelism (PostgreSQL):**
- PostgreSQL CDC uses logical replication which is single-threaded per slot
- Use multiple slots for different tables:
  ```json
  "slot.name": "debezium_slot_orders",
  "table.include.list": "public.orders"
  ```

**Batch Configuration:**
```json
"poll.interval.ms": 100,
"batch.size": 2048,
"max.batch.size": 16384
```

**Performance Monitoring:**
```promql
# Check if tasks are balanced
kafka_connect_connector_tasks_total{state="RUNNING"}

# Monitor lag per table
kafka_connect_connect_worker_metrics_task_offset_lag_consumer

# Track throughput
rate(kafka_connect_connect_worker_metrics_messages_consumed_total[5m])
```

**Scaling Guidelines:**
| Data Volume | Tasks | Memory |
|-------------|-------|--------|
| < 1M rows/day | 1 | 1GB |
| 1-10M rows/day | 2-3 | 2GB |
| > 10M rows/day | 3-5 + partitioning | 4GB+ |

---

### Q17: What strategies reduce Debezium's impact on source databases?

**Answer:**

1. **MySQL - Use RBR (Row-Based Replication):**
   ```sql
   binlog-format = ROW
   ```
   RBR captures only changed rows, not full queries.

2. **Minimize Snapshot Frequency:**
   ```json
   "snapshot.locking.mode": "none"
   "snapshot.fetch.size": 10000
   ```

3. **PostgreSQL - Optimize Replication Slots:**
   ```sql
   -- Monitor slot lag
   SELECT slot_name, pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), confirmed_flush_lsn)) 
   FROM pg_replication_slots;
   
   -- Set retention
   -- wal_keep_size = 1GB (keep WAL files for replication)
   ```

4. **Batch Processing:**
   ```json
   "max.batch.size": 10240
   "max.queue.size.in.bytes": 10485760
   ```

5. **Filter Unneeded Tables:**
   ```json
   "table.exclude.list": "inventory.logs,inventory.audit"
   ```

6. **Snapshot vs. Incremental:**
   ```json
   "snapshot.mode": "schema_only"  // After initial sync
   ```

7. **Read Replica as CDC Source:**
   - Point Debezium at a replica, not primary
   - Reduces load on production master
   - Adds small replication lag acceptable for CDC
