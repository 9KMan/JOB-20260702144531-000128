const { Kafka } = require('kafkajs')

const kafka = new Kafka({
  clientId: 'demo-producer',
  brokers: ['localhost:9092'],
})

const producer = kafka.producer()

async function produce(topic, messages) {
  await producer.connect()
  console.log('Producer connected')

  await producer.send({
    topic,
    messages: messages.map(m => ({
      key: m.key,
      value: JSON.stringify(m.value),
      headers: m.headers || {},
    })),
  })

  console.log(`Produced ${messages.length} messages to ${topic}`)
  await producer.disconnect()
}

// CLI usage: node producer.js <topic> <count>
const topic = process.argv[2] || 'demo-topic'
const count = parseInt(process.argv[3]) || 10

const messages = Array.from({ length: count }, (_, i) => ({
  key: `key-${i}`,
  value: {
    event: 'demo-event',
    timestamp: new Date().toISOString(),
    data: { id: i, message: `Hello Kafka ${i}` }
  }
}))

produce(topic, messages).catch(console.error)
