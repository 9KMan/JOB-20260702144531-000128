# Local Kafka Development Configuration
module.exports = {
  kafka: {
    clientId: 'local-kafka-client',
    brokers: [process.env.KAFKA_BROKER || 'localhost:9092'],
    connectionTimeout: 3000,
    retry: {
      initialRetryTime: 100,
      retries: 8
    }
  },
  schemaRegistry: {
    url: process.env.SCHEMA_REGISTRY_URL || 'http://localhost:8081'
  },
  topics: {
    demo: process.env.LOCAL_TOPIC || 'demo-topic',
    events: 'events-topic',
    dlq: 'events.DLQ'
  },
  consumer: {
    groupId: process.env.CONSUMER_GROUP_ID || 'local-consumer-group',
    sessionTimeout: 30000,
    heartbeatInterval: 3000
  }
}
