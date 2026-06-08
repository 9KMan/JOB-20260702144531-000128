const { Kafka } = require('kafkajs')
const localConfig = require('../config/local.config')

class StreamProcessor {
  constructor() {
    this.kafka = new Kafka(localConfig.kafka)
    this.producer = this.kafka.producer()
    this.consumer = this.kafka.consumer({ groupId: `${localConfig.consumer.groupId}-processor` })
    this.transformers = []
  }

  async connect() {
    await this.producer.connect()
    await this.consumer.connect()
    console.log('Stream processor connected')
  }

  async disconnect() {
    await this.producer.disconnect()
    await this.consumer.disconnect()
  }

  addTransformer(name, transformer) {
    this.transformers.push({ name, transformer })
    console.log(`Transformer '${name}' added`)
  }

  async process(sourceTopic, targetTopic) {
    await this.consumer.subscribe({ topic: sourceTopic, fromBeginning: false })

    await this.consumer.run({
      eachMessage: async ({ topic, partition, message }) => {
        try {
          const value = JSON.parse(message.value.toString())
          console.log(`Processing message from ${topic}:`, value)

          // Apply all transformers in sequence
          let transformedValue = value
          for (const { name, transformer } of this.transformers) {
            transformedValue = await transformer(transformedValue)
            console.log(`Applied transformer '${name}'`)
          }

          // Send to target topic
          await this.producer.send({
            topic: targetTopic,
            messages: [{
              key: message.key,
              value: JSON.stringify(transformedValue),
              headers: {
                ...message.headers,
                'processed-by': 'stream-processor',
                'original-topic': topic
              }
            }]
          })

          console.log(`Sent processed message to ${targetTopic}`)
        } catch (error) {
          console.error(`Error processing message:`, error.message)
          // In production, send to DLQ here
          throw error
        }
      }
    })
  }

  // Aggregate messages by key within a time window
  createAggregator(keyField, aggregateFn, windowMs) {
    const buffers = new Map()

    return async (value) => {
      const key = value[keyField]
      const now = Date.now()

      if (!buffers.has(key)) {
        buffers.set(key, { values: [], expiry: now + windowMs })
      }

      const buffer = buffers.get(key)
      buffer.values.push(value)

      // Clean expired entries
      if (now > buffer.expiry) {
        const aggregated = buffer.values.reduce(aggregateFn, {})
        buffers.delete(key)
        return aggregated
      }

      return null // Not yet ready
    }
  }
}

module.exports = StreamProcessor
