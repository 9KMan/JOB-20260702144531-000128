# Confluent Cloud Configuration
# Fill in your Confluent Cloud credentials
module.exports = {
  kafka: {
    clientId: 'confluent-cloud-client',
    brokers: [process.env.CLOUD_KAFKA_BROKER],
    ssl: {
      rejectUnauthorized: false
    },
    sasl: {
      mechanism: 'plain',
      username: process.env.CLOUD_API_KEY,
      password: process.env.CLOUD_API_SECRET
    }
  },
  schemaRegistry: {
    url: process.env.CLOUD_SCHEMA_REGISTRY_URL,
    auth: {
      username: process.env.CLOUD_SCHEMA_REGISTRY_KEY,
      password: process.env.CLOUD_SCHEMA_REGISTRY_SECRET
    }
  },
  topics: {
    events: process.env.CLOUD_TOPIC || 'events-topic',
    dlq: process.env.CLOUD_TOPIC_DLQ || 'events.DLQ'
  },
  consumer: {
    groupId: process.env.CLOUD_CONSUMER_GROUP || 'cloud-consumer-group'
  }
}
