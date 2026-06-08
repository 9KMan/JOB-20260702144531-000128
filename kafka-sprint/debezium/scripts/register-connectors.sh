#!/bin/bash
# Register Debezium Connectors

CONNECT_URL="http://localhost:8083"

echo "Waiting for Kafka Connect to be ready..."
until curl -s -f "${CONNECT_URL}/" > /dev/null; do
    echo "Still waiting..."
    sleep 5
done
echo "Kafka Connect is ready!"

# Register MySQL Source Connector
echo "Registering MySQL Source Connector..."
curl -i -X POST -H "Accept:application/json" \
    -H "Content-Type:application/json" \
    "${CONNECT_URL}/connectors/" \
    -d @/opt/kafka/connect-custom/mysql-source-connector.json

echo ""
echo "MySQL Connector registered!"

# Wait a bit before registering next connector
sleep 2

# Register PostgreSQL Source Connector
echo "Registering PostgreSQL Source Connector..."
curl -i -X POST -H "Accept:application/json" \
    -H "Content-Type:application/json" \
    "${CONNECT_URL}/connectors/" \
    -d @/opt/kafka/connect-custom/postgres-source-connector.json

echo ""
echo "PostgreSQL Connector registered!"

# List all connectors
echo ""
echo "Current connectors:"
curl -s "${CONNECT_URL}/connectors?expand=info" | jq '.'

# Check connector status
echo ""
echo "Connector statuses:"
echo "MySQL:" 
curl -s "${CONNECT_URL}/connectors/mysql-source-connector/status" | jq '.'
echo ""
echo "PostgreSQL:"
curl -s "${CONNECT_URL}/connectors/postgres-source-connector/status" | jq '.'
