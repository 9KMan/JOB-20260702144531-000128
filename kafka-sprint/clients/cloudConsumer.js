const { Kafka } = require('kafkajs')
const cloudConfig = require('../config/cloud.config')

class CloudConsumer {
  constructor() {
    this.kafka = new Kafka(cloudConfig.kafka)
    this.consumer = this.kafka.consumer({ groupId: cloudConfig.consumer.groupId })
  }

  async connect() {
    await this.consumer.connect()
    console.log('Cloud consumer connected')
  }

  async disconnect() {
    await this.consumer.disconnect()
  }

  async subscribe(topics) {
    for (const topic of topics) {
      await this.consumer.subscribe({ topic, fromBeginning: false })
      console.log(`Subscribed to ${topic}`)
    }
  }

  async run(handler) {
    await this.consumer.run({
      eachMessage: async ({ topic, partition, message }) => {
        const value = JSON.parse(message.value.toString())
        await handler({ topic, partition, key: message.key?.toString(), value, headers: message.headers })
      }
    })
  }
}

module.exports = CloudConsumer
