const { Kafka, logLevel } = require('kafkajs')
const { SchemaRegistry } = require('@confluentinc/schema-registry')
const localConfig = require('../config/local.config')

class SchemaRegistryClient {
  constructor() {
    this.kafka = new Kafka({
      ...localConfig.kafka,
      logLevel: logLevel.WARN
    })
    this.producer = this.kafka.producer()
    this.schemaRegistry = new SchemaRegistry({
      host: localConfig.schemaRegistry.url
    })
  }

  async connect() {
    await this.producer.connect()
    console.log('Producer connected')
  }

  async disconnect() {
    await this.producer.disconnect()
  }

  async registerSchema(topic, schema) {
    const { id } = await this.schemaRegistry.register({
      type: 'JSON',
      schema: JSON.stringify(schema)
    }, { topic })
    console.log(`Schema registered with ID: ${id}`)
    return id
  }

  async encode(topic, schema, data) {
    const { id } = await this.schemaRegistry.register({
      type: 'JSON',
      schema: JSON.stringify(schema)
    }, { topic })
    return await this.schemaRegistry.encode(id, data)
  }

  async decode(buffer) {
    return await this.schemaRegistry.decode(buffer)
  }

  async sendValidated(topic, schema, data) {
    const encodedValue = await this.encode(topic, schema, data)
    await this.producer.send({
      topic,
      messages: [{ value: encodedValue }]
    })
    console.log(`Sent validated message to ${topic}`)
  }
}

module.exports = SchemaRegistryClient
