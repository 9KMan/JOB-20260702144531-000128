#!/bin/bash
# Kafka Topic Creation Script

KAFKA_BIN=/opt/homebrew/bin

# Create topics
docker exec kafka-broker kafka-topics   --bootstrap-server localhost:9092   --create   --topic demo-topic   --partitions 3   --replication-factor 1

docker exec kafka-broker kafka-topics   --bootstrap-server localhost:9092   --create   --topic events-topic   --partitions 3   --replication-factor 1

docker exec kafka-broker kafka-topics   --bootstrap-server localhost:9092   --create   --topic events.DLQ   --partitions 3   --replication-factor 1

# List all topics
docker exec kafka-broker kafka-topics   --bootstrap-server localhost:9092   --list

echo 'Topics created successfully'
