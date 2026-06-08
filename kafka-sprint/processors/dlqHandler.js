const { Kafka } = require('kafkajs')
const localConfig = require('../config/local.config')

class DLQHandler {
  constructor() {
    this.kafka = new Kafka(localConfig.kafka)
    this.producer = this.kafka.producer()
    this.dlqTopic = localConfig.topics.dlq
  }

  async connect() {
    await this.producer.connect()
    console.log('DLQ handler producer connected')
  }

  async disconnect() {
    await this.producer.disconnect()
  }

  async sendToDLQ(originalTopic, originalMessage, error, retryCount = 0) {
    const dlqMessage = {
      originalTopic,
      originalPartition: originalMessage.partition,
      originalOffset: originalMessage.offset,
      originalKey: originalMessage.key?.toString(),
      originalValue: originalMessage.value?.toString(),
      error: {
        message: error.message,
        stack: error.stack,
        name: error.name
      },
      retryCount,
      failedAt: new Date().toISOString(),
      headers: {
        'x-original-topic': originalTopic,
        'x-error-message': error.message.substring(0, 200),
        'x-retry-count': retryCount.toString()
      }
    }

    await this.producer.send({
      topic: this.dlqTopic,
      messages: [{
        key: originalMessage.key?.toString() || `dlq-${Date.now()}`,
        value: JSON.stringify(dlqMessage),
        headers: dlqMessage.headers
      }]
    })

    console.log(`Message sent to DLQ: ${this.dlqTopic}`)
  }

  // Process DLQ messages for retry or alerting
  async processDLQ(handler) {
    const consumer = this.kafka.consumer({ groupId: 'dlq-processor-group' })
    await consumer.connect()
    await consumer.subscribe({ topic: this.dlqTopic, fromBeginning: false })

    await consumer.run({
      eachMessage: async ({ topic, partition, message }) => {
        const dlqEntry = JSON.parse(message.value.toString())
        console.log(`DLQ entry received:`, dlqEntry)

        await handler(dlqEntry)
      }
    })
  }
}

module.exports = DLQHandler
