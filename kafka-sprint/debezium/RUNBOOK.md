# Debezium CDC Runbook

## Quick Start

### 1. Start the Environment

```bash
cd kafka-sprint/debezium
docker-compose up -d
```

Wait for all services to be healthy:
```bash
docker-compose ps
```

### 2. Register Connectors

```bash
docker exec -it kafka-connect \
  curl -X POST -H "Content-Type: application/json" \
  -d @/opt/kafka/connect-custom/mysql-source-connector.json \
  http://localhost:8083/connectors/
```

### 3. Verify CDC is Working

Check Kafka topics for CDC events:
```bash
docker exec kafka-broker kafka-topics --list --bootstrap-server localhost:9092
```

Consume MySQL CDC events:
```bash
docker exec -it kafka-broker kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic mysql.inventory.customers \
  --from-beginning
```

## Common Operations

### Restart a Connector
```bash
curl -X POST http://localhost:8083/connectors/mysql-source-connector/restart
```

### Pause a Connector
```bash
curl -X PUT http://localhost:8083/connectors/mysql-source-connector/pause
```

### Resume a Connector
```bash
curl -X PUT http://localhost:8083/connectors/mysql-source-connector/resume
```

### Delete a Connector
```bash
curl -X DELETE http://localhost:8083/connectors/mysql-source-connector
```

### Check Connector Status
```bash
curl -s http://localhost:8083/connectors/mysql-source-connector/status | jq '.'
```

### List All Connectors
```bash
curl -s http://localhost:8083/connectors | jq '.'
```

## Testing CDC

### MySQL Operations
```bash
docker exec -it mysql mysql -u root -pdebezium inventory

-- Insert
INSERT INTO customers (first_name, last_name, email) VALUES ('Test', 'User', 'test@example.com');

-- Update
UPDATE customers SET phone = '+1-555-9999' WHERE email = 'test@example.com';

-- Delete
DELETE FROM customers WHERE email = 'test@example.com';
```

### PostgreSQL Operations
```bash
docker exec -it postgres psql -U postgres -d inventory

-- Insert
INSERT INTO products (sku, name, price, stock_quantity) VALUES ('TEST-001', 'Test Product', 9.99, 10);

-- Update
UPDATE products SET price = 14.99 WHERE sku = 'TEST-001';

-- Delete
DELETE FROM products WHERE sku = 'TEST-001';
```

## Monitoring

### Access Grafana
- URL: http://localhost:3001
- Username: admin
- Password: admin

### Access Kafka UI
- URL: http://localhost:8090

### Prometheus Metrics
- Kafka Connect: http://localhost:8083/metrics
- Kafka Exporter: http://localhost:9308/metrics

## Stopping the Environment

```bash
docker-compose down
```

To remove all data volumes:
```bash
docker-compose down -v
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| MYSQL_ROOT_PASSWORD | MySQL root password | debezium |
| MYSQL_USER | Debezium MySQL user | debezium |
| MYSQL_PASSWORD | Debezium MySQL password | dbz123 |
| DATABASE_HOSTNAME | Source database hostname | mysql/postgres |
| KAFKA_BOOTSTRAP_SERVERS | Kafka broker address | kafka:9092 |
| CONNECT_BOOTSTRAP_SERVERS | Kafka Connect bootstrap servers | kafka:9092 |
