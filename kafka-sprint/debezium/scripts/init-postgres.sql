-- PostgreSQL CDC Demo Database Setup

-- Create tables
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price NUMERIC(10, 2) NOT NULL,
    stock_quantity INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    customer_id INT NOT NULL,
    order_number VARCHAR(50) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'shipped', 'delivered', 'cancelled')),
    total_amount NUMERIC(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    shipping_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INT NOT NULL REFERENCES orders(id),
    product_id INT NOT NULL REFERENCES products(id),
    quantity INT NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL
);

-- Create outbox table for reliable event delivery
CREATE TABLE IF NOT EXISTS outbox (
    id SERIAL PRIMARY KEY,
    aggregate_type VARCHAR(100) NOT NULL,
    aggregate_id VARCHAR(100) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    occurred_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT FALSE
);

-- Create index on outbox for efficient polling
CREATE INDEX IF NOT EXISTS outbox_unprocessed ON outbox(processed, occurred_on) WHERE processed = FALSE;

-- Insert sample data
INSERT INTO customers (first_name, last_name, email, phone) VALUES
('Alice', 'Brown', 'alice.brown@example.com', '+1-555-0201'),
('Charlie', 'Wilson', 'charlie.wilson@example.com', '+1-555-0202'),
('Diana', 'Miller', 'diana.miller@example.com', '+1-555-0203');

INSERT INTO products (sku, name, description, price, stock_quantity) VALUES
('PROD-P-001', 'Widget Pro', 'Professional grade widget', 49.99, 80),
('PROD-P-002', 'Gadget Plus', 'Enhanced gadget version', 59.99, 60),
('PROD-P-003', 'Tool Max', 'Maximum performance tool', 79.99, 40);

INSERT INTO orders (customer_id, order_number, status, total_amount, currency, shipping_address) VALUES
(1, 'PG-ORD-001', 'confirmed', 109.98, 'USD', '789 Pine St, Nowhere, USA'),
(2, 'PG-ORD-002', 'shipped', 59.99, 'USD', '321 Elm Blvd, Elsewhere, USA');

INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(1, 1, 2, 49.99),
(1, 2, 1, 59.99),
(2, 2, 1, 59.99);

-- Create publication for logical replication (required for Debezium)
DROP PUBLICATION IF EXISTS dbz_publication;
CREATE PUBLICATION dbz_publication FOR ALL TABLES;

-- Create replication slot
SELECT pg_create_logical_replication_slot('debezium_slot', 'pgoutput');
