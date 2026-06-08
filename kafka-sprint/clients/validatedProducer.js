const SchemaRegistryClient = require('./schemaRegistryClient')
const orderEventSchema = require('../schemas/order-event.schema.json')

class ValidatedProducer {
  constructor() {
    this.client = new SchemaRegistryClient()
  }

  async connect() {
    await this.client.connect()
  }

  async disconnect() {
    await this.client.disconnect()
  }

  async sendOrderEvent(orderData) {
    const event = {
      eventId: orderData.eventId,
      eventType: orderData.eventType,
      orderId: orderData.orderId,
      customerId: orderData.customerId,
      timestamp: new Date().toISOString(),
      totalAmount: orderData.totalAmount,
      currency: orderData.currency || 'USD',
      items: orderData.items || [],
      shippingAddress: orderData.shippingAddress,
      metadata: orderData.metadata || {}
    }

    await this.client.sendValidated('events-topic', orderEventSchema, event)
    console.log(`Order event sent: ${event.eventType} for order ${event.orderId}`)
  }
}

module.exports = ValidatedProducer
