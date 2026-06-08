const { Kafka } = require('kafkajs')
const { SchemaRegistry } = require('@confluentinc/schema-registry')
const localConfig = require('../config/local.config')

class ValidatedConsumer {
  constructor() {
    this.kafka = new Kafka(localConfig.kafka)
    this.consumer = this.kafka.consumer({ groupId: `${localConfig.consumer.groupId}-validated` })
    this.schemaRegistry = new SchemaRegistry({
      host: localConfig.schemaRegistry.url
    })
    this.handlers = new Map()
  }

  async connect() {
    await this.consumer.connect()
    console.log('Consumer connected')
  }

  async disconnect() {
    await this.consumer.disconnect()
  }

  registerHandler(eventType, handler) {
    this.handlers.set(eventType, handler)
    console.log(`Handler registered for ${eventType}`)
  }

  async subscribe(topics) {
    for (const topic of topics) {
      await this.consumer.subscribe({ topic, fromBeginning: false })
      console.log(`Subscribed to ${topic}`)
    }
  }

  async run() {
    await this.consumer.run({
      eachMessage: async ({ topic, partition, message }) => {
        try {
          const decodedValue = await this.schemaRegistry.decode(message.value)
          console.log(`[${topic}:${partition}] Decoded:`, decodedValue)

          const handler = this.handlers.get(decodedValue.eventType)
          if (handler) {
            await handler(decodedValue)
          } else {
            console.log(`No handler for event type: ${decodedValue.eventType}`)
          }
        } catch (error) {
          console.error(`Error processing message:`, error.message)
          throw error
        }
      }
    })
  }
}

module.exports = ValidatedConsumer
