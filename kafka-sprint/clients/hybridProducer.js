const { Kafka } = require('kafkajs')
const localConfig = require('../config/local.config')
const cloudConfig = require('../config/cloud.config')

class HybridProducer {
  constructor() {
    this.localKafka = new Kafka(localConfig.kafka)
    this.cloudKafka = new Kafka(cloudConfig.kafka)
    this.localProducer = this.localKafka.producer()
    this.cloudProducer = this.cloudKafka.producer()
    this.environment = process.env.CLIENT_TYPE || 'local'
  }

  async connect() {
    if (this.environment === 'local' || this.environment === 'both') {
      await this.localProducer.connect()
      console.log('Local producer connected')
    }
    if (this.environment === 'cloud' || this.environment === 'both') {
      await this.cloudProducer.connect()
      console.log('Cloud producer connected')
    }
  }

  async disconnect() {
    if (this.environment === 'local' || this.environment === 'both') {
      await this.localProducer.disconnect()
    }
    if (this.environment === 'cloud' || this.environment === 'both') {
      await this.cloudProducer.disconnect()
    }
  }

  async send(topic, messages) {
    const results = []
    const kafkaMessage = messages.map(m => ({
      key: m.key,
      value: JSON.stringify(m.value),
      headers: m.headers || {}
    }))

    if (this.environment === 'local' || this.environment === 'both') {
      const localTopic = this.environment === 'both' ? `local.${topic}` : topic
      const result = await this.localProducer.send({
        topic: localTopic,
        messages: kafkaMessage
      })
      results.push({ environment: 'local', topic: localTopic, result })
      console.log(`Produced to local.${topic}`)
    }

    if (this.environment === 'cloud' || this.environment === 'both') {
      const cloudTopic = this.environment === 'both' ? `cloud.${topic}` : topic
      const result = await this.cloudProducer.send({
        topic: cloudTopic,
        messages: kafkaMessage
      })
      results.push({ environment: 'cloud', topic: cloudTopic, result })
      console.log(`Produced to cloud.${topic}`)
    }

    return results
  }
}

module.exports = HybridProducer
