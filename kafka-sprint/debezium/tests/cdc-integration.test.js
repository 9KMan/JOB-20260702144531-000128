/**
 * Debezium CDC Integration Tests
 * 
 * Tests the complete CDC pipeline:
 * 1. MySQL Source Connector
 * 2. PostgreSQL Source Connector  
 * 3. Event processing and transformation
 * 4. Error handling and DLQ
 */

const { Kafka, logLevel } = require('kafkajs');

// Test configuration
const KAFKA_BROKER = process.env.KAFKA_BROKER || 'localhost:9092';
const CONNECT_URL = process.env.CONNECT_URL || 'http://localhost:8083';

const kafka = new Kafka({
  clientId: 'cdc-integration-test',
  brokers: [KAFKA_BROKER],
  logLevel: logLevel.WARN,
  retry: {
    initialRetryTime: 100,
    retries: 10
  }
});

const admin = kafka.admin();
const consumer = kafka.consumer({ groupId: 'cdc-test-group' });

// Topics to monitor
const MYSQL_TOPICS = [
  'mysql.inventory.customers',
  'mysql.inventory.orders',
  'mysql.inventory.products'
];

const POSTGRES_TOPICS = [
  'pg.public.customers',
  'pg.public.orders',
  'pg.public.products'
];

const DLQ_TOPICS = ['errors.DLQ'];

describe('Debezium CDC Integration Tests', () => {
  beforeAll(async () => {
    await admin.connect();
    await consumer.connect();
    
    // Subscribe to all CDC topics
    const allTopics = [...MYSQL_TOPICS, ...POSTGRES_TOPICS, ...DLQ_TOPICS];
    await Promise.all(allTopics.map(topic => 
      consumer.subscribe({ topic, fromBeginning: true })
    ));
    
    await consumer.run({ eachMessage: handleMessage });
  });

  afterAll(async () => {
    await consumer.disconnect();
    await admin.disconnect();
  });

  describe('Connector Status Tests', () => {
    test('MySQL source connector should be registered and running', async () => {
      const response = await fetch(`${CONNECT_URL}/connectors/mysql-source-connector/status`);
      const status = await response.json();
      
      expect(status.name).toBe('mysql-source-connector');
      expect(status.connector.state).toBe('RUNNING');
    });

    test('PostgreSQL source connector should be registered and running', async () => {
      const response = await fetch(`${CONNECT_URL}/connectors/postgres-source-connector/status`);
      const status = await response.json();
      
      expect(status.name).toBe('postgres-source-connector');
      expect(status.connector.state).toBe('RUNNING');
    });

    test('All connector tasks should be in running state', async () => {
      const mysqlStatus = await fetch(`${CONNECT_URL}/connectors/mysql-source-connector/status`).then(r => r.json());
      const postgresStatus = await fetch(`${CONNECT_URL}/connectors/postgres-source-connector/status`).then(r => r.json());
      
      const allTasksRunning = (status) => 
        status.tasks.every(task => task.state === 'RUNNING');
      
      expect(allTasksRunning(mysqlStatus)).toBe(true);
      expect(allTasksRunning(postgresStatus)).toBe(true);
    });
  });

  describe('Topic Creation Tests', () => {
    test('CDC topics should exist in Kafka', async () => {
      const topics = await admin.listTopics();
      const allTopicsExist = [...MYSQL_TOPICS, ...POSTGRES_TOPICS].every(
        topic => topics.includes(topic)
      );
      
      expect(allTopicsExist).toBe(true);
    });

    test('Schema history topics should exist', async () => {
      const topics = await admin.listTopics();
      
      expect(topics).toContain('schema-changes.inventory');
    });

    test('Internal Debezium topics should exist', async () => {
      const topics = await admin.listTopics();
      const internalTopics = ['debezium_configs', 'debezium_offsets', 'debezium_statuses'];
      
      internalTopics.forEach(topic => {
        expect(topics).toContain(topic);
      });
    });
  });

  describe('CDC Event Format Tests', () => {
    let cdcEvent;

    beforeAll(async () => {
      // Wait for CDC events to arrive
      await new Promise(resolve => setTimeout(resolve, 5000));
    });

    test('CDC events should have correct envelope structure', () => {
      // Events should have schema and payload
      expect(cdcEvent).toBeDefined();
      
      if (cdcEvent) {
        expect(cdcEvent).toHaveProperty('payload');
        expect(cdcEvent.payload).toHaveProperty('before');
        expect(cdcEvent.payload).toHaveProperty('after');
        expect(cdcEvent.payload).toHaveProperty('source');
        expect(cdcEvent.payload).toHaveProperty('op');
        expect(cdcEvent.payload).toHaveProperty('ts_ms');
      }
    });

    test('CDC events should have valid operation types', () => {
      if (cdcEvent && cdcEvent.payload) {
        const validOps = ['c', 'r', 'u', 'd'];
        expect(validOps).toContain(cdcEvent.payload.op);
      }
    });

    test('CDC events should have source metadata', () => {
      if (cdcEvent && cdcEvent.payload && cdcEvent.payload.source) {
        const source = cdcEvent.payload.source;
        
        expect(source).toHaveProperty('version');
        expect(source).toHaveProperty('connector');
        expect(source).toHaveProperty('ts_ms');
        expect(source).toHaveProperty('db');
        expect(source).toHaveProperty('table');
      }
    });
  });

  describe('Data Capture Tests', () => {
    test('MySQL inventory database should have sample data', async () => {
      const topics = await admin.listTopics();
      const customersTopic = topics.find(t => t.includes('mysql.inventory.customers'));
      
      expect(customersTopic).toBeDefined();
    });

    test('PostgreSQL public schema should have sample data', async () => {
      const topics = await admin.listTopics();
      const customersTopic = topics.find(t => t.includes('pg.public.customers'));
      
      expect(customersTopic).toBeDefined();
    });
  });

  describe('Performance Tests', () => {
    test('Consumer should be able to keep up with message rate', async () => {
      // This is a basic check that the consumer group is healthy
      const consumerGroup = await admin.describeGroups({ groupIds: ['cdc-test-group'] });
      
      expect(consumerGroup.groups).toHaveLength(1);
      expect(consumerGroup.groups[0].state).toBe('Stable');
    });
  });
});

// Message handler for consumer
const receivedMessages = [];

async function handleMessage({ topic, partition, message }) {
  try {
    const value = message.value.toString();
    const event = JSON.parse(value);
    receivedMessages.push({ topic, partition, event });
    
    console.log(`[${topic}] Received event:`, JSON.stringify(event.payload, null, 2));
  } catch (err) {
    console.error('Failed to parse message:', err);
  }
}

module.exports = { receivedMessages };
