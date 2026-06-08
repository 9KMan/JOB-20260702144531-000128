const { Kafka } = require('kafkajs')
const localConfig = require('../config/local.config')

describe('Kafka Integration Tests', () => {
  let kafka
  let producer
  let consumer
  const testTopic = 'test-integration-topic'
  const testMessages = []

  beforeAll(async () => {
    kafka = new Kafka(localConfig.kafka)
    producer = kafka.producer()
    consumer = kafka.consumer({ groupId: 'test-group' })
    
    await producer.connect()
    await consumer.connect()
  })

  afterAll(async () => {
    await producer.disconnect()
    await consumer.disconnect()
  })

  beforeEach(() => {
    testMessages.length = 0
  })

  test('should produce and consume messages', async () => {
    // Produce messages
    const messages = Array.from({ length: 5 }, (_, i) => ({
      key: `key-${i}`,
      value: JSON.stringify({ id: i, data: `message-${i}`, timestamp: Date.now() })
    }))

    await producer.send({
      topic: testTopic,
      messages
    })

    // Consume messages
    const consumed = []
    await consumer.subscribe({ topic: testTopic, fromBeginning: true })

    const consumePromise = new Promise((resolve) => {
      consumer.run({
        eachMessage: async ({ message }) => {
          consumed.push({
            key: message.key.toString(),
            value: JSON.parse(message.value.toString())
          })
          if (consumed.length === messages.length) {
            resolve()
          }
        }
      })
    })

    await expect(consumePromise).resolves.toBeUndefined()
    expect(consumed).toHaveLength(5)
  })

  test('should maintain message ordering within partition', async () => {
    const partition = 0
    const messages = Array.from({ length: 10 }, (_, i) => ({
      key: null,
      value: JSON.stringify({ sequence: i, timestamp: Date.now() })
    }))

    await producer.send({
      topic: testTopic,
      messages,
      partition
    })

    const consumed = []
    await consumer.subscribe({ topic: testTopic, fromBeginning: true })

    const consumePromise = new Promise((resolve) => {
      let count = 0
      consumer.run({
        eachMessage: async ({ message, partition: p }) => {
          if (p === partition) {
            consumed.push(JSON.parse(message.value.toString()))
            count++
            if (count === 10) resolve()
          }
        }
      })
    })

    await expect(consumePromise).resolves.toBeUndefined()
    
    // Verify ordering
    for (let i = 0; i < consumed.length - 1; i++) {
      expect(consumed[i].sequence).toBeLessThan(consumed[i + 1].sequence)
    }
  })

  test('should handle message headers', async () => {
    const headers = {
      'x-test-header': 'test-value',
      'x-correlation-id': 'corr-123'
    }

    await producer.send({
      topic: testTopic,
      messages: [{
        key: 'header-test',
        value: JSON.stringify({ test: true }),
        headers
      }]
    })

    let receivedHeaders = null
    await consumer.subscribe({ topic: testTopic, fromBeginning: true })

    const headerPromise = new Promise((resolve) => {
      consumer.run({
        eachMessage: async ({ message }) => {
          if (message.key?.toString() === 'header-test') {
            receivedHeaders = message.headers
            resolve()
          }
        }
      })
    })

    await expect(headerPromise).resolves.toBeUndefined()
    expect(receivedHeaders['x-test-header'].toString()).toBe('test-value')
    expect(receivedHeaders['x-correlation-id'].toString()).toBe('corr-123')
  })
})
