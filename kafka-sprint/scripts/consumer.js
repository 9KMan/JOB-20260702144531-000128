const { Kafka } = require('kafkajs')

const kafka = new Kafka({
  clientId: 'demo-consumer',
  brokers: ['localhost:9092'],
  retry: {
    initialRetryTime: 100,
    retries: 8
  }
})

const consumer = kafka.consumer({
  groupId: 'demo-consumer-group',
  sessionTimeout: 30000,
  heartbeatInterval: 3000,
})

async function consume(topic) {
  await consumer.connect()
  console.log('Consumer connected')

  await consumer.subscribe({ topic, fromBeginning: true })

  await consumer.run({
    eachMessage: async ({ topic, partition, message }) => {
      console.log(`[${topic}:${partition}] key=${message.key?.toString()} value=${message.value.toString()}`)
    },
  })
}

const topic = process.argv[2] || 'demo-topic'
consume(topic).catch(console.error)
