-- Initialize PostgreSQL with sample e-commerce data
-- This script runs automatically when the postgres container starts

-- Create the ecommerce database (if not exists)
\c ecommerce;

-- Create users table
CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    full_name VARCHAR(200),
    customer_tier VARCHAR(20) CHECK (customer_tier IN ('bronze', 'silver', 'gold', 'platinum')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create products table
CREATE TABLE IF NOT EXISTS products (
    product_id VARCHAR(50) PRIMARY KEY,
    product_name VARCHAR(255),
    category VARCHAR(100),
    brand VARCHAR(100),
    cost NUMERIC(10, 2),
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create orders table
CREATE TABLE IF NOT EXISTS orders (
    order_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50) REFERENCES customers(customer_id),
    order_date TIMESTAMP NOT NULL,
    status VARCHAR(20) CHECK (status IN ('pending', 'processing', 'shipped', 'delivered', 'cancelled')),
    total_amount NUMERIC(10, 2) NOT NULL,
    shipping_address TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create order_items table
CREATE TABLE IF NOT EXISTS order_items (
    order_item_id VARCHAR(50) PRIMARY KEY,
    order_id VARCHAR(50) REFERENCES orders(order_id),
    product_id VARCHAR(50) REFERENCES products(product_id),
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample customers
INSERT INTO customers (customer_id, email, first_name, last_name, full_name, customer_tier, created_at)
VALUES 
    ('C001', 'alice@example.com', 'Alice', 'Johnson', 'Alice Johnson', 'gold', '2024-01-15'),
    ('C002', 'bob@example.com', 'Bob', 'Smith', 'Bob Smith', 'silver', '2024-02-01'),
    ('C003', 'carol@example.com', 'Carol', 'Williams', 'Carol Williams', 'platinum', '2024-01-01'),
    ('C004', 'david@example.com', 'David', 'Brown', 'David Brown', 'bronze', '2024-03-01'),
    ('C005', 'eve@example.com', 'Eve', 'Davis', 'Eve Davis', 'gold', '2024-02-15')
ON CONFLICT (customer_id) DO NOTHING;

-- Insert sample products
INSERT INTO products (product_id, product_name, category, brand, cost)
VALUES 
    ('P001', 'Wireless Mouse', 'Electronics', 'LogiTech', 15.00),
    ('P002', 'Mechanical Keyboard', 'Electronics', 'Corsair', 65.00),
    ('P003', 'USB-C Cable', 'Accessories', 'Anker', 8.00),
    ('P004', 'Monitor Stand', 'Furniture', 'ErGear', 45.00),
    ('P005', 'Desk Lamp', 'Furniture', 'BenQ', 85.00),
    ('P006', 'Webcam HD', 'Electronics', 'LogiTech', 55.00),
    ('P007', 'Headphones', 'Audio', 'Sony', 120.00),
    ('P008', 'Mouse Pad', 'Accessories', 'SteelSeries', 12.00)
ON CONFLICT (product_id) DO NOTHING;

-- Insert sample orders
INSERT INTO orders (order_id, customer_id, order_date, status, total_amount, shipping_address, loaded_at)
VALUES 
    ('O001', 'C001', '2025-01-10 10:30:00', 'delivered', 158.00, '123 Main St, NYC', '2025-01-10 11:00:00'),
    ('O002', 'C002', '2025-01-12 14:20:00', 'shipped', 73.00, '456 Oak Ave, LA', '2025-01-12 15:00:00'),
    ('O003', 'C003', '2025-01-15 09:00:00', 'delivered', 205.00, '789 Pine Rd, Chicago', '2025-01-15 10:00:00'),
    ('O004', 'C001', '2025-01-18 16:45:00', 'processing', 92.00, '123 Main St, NYC', '2025-01-18 17:00:00'),
    ('O005', 'C004', '2025-01-20 11:30:00', 'pending', 27.00, '321 Elm St, Houston', '2025-01-20 12:00:00'),
    ('O006', 'C005', '2025-01-22 08:15:00', 'shipped', 285.00, '654 Maple Dr, Seattle', '2025-01-22 09:00:00'),
    ('O007', 'C002', '2025-01-25 13:00:00', 'delivered', 65.00, '456 Oak Ave, LA', '2025-01-25 14:00:00'),
    ('O008', 'C003', '2025-02-01 10:00:00', 'delivered', 120.00, '789 Pine Rd, Chicago', '2025-02-01 11:00:00')
ON CONFLICT (order_id) DO NOTHING;

-- Insert sample order items
INSERT INTO order_items (order_item_id, order_id, product_id, quantity, unit_price, loaded_at)
VALUES 
    ('OI001', 'O001', 'P001', 1, 25.00, '2025-01-10 11:00:00'),
    ('OI002', 'O001', 'P003', 1, 12.00, '2025-01-10 11:00:00'),
    ('OI003', 'O001', 'P008', 1, 15.00, '2025-01-10 11:00:00'),
    ('OI004', 'O002', 'P002', 1, 89.00, '2025-01-12 15:00:00'),
    ('OI005', 'O002', 'P003', 2, 12.00, '2025-01-12 15:00:00'),
    ('OI006', 'O003', 'P004', 1, 65.00, '2025-01-15 10:00:00'),
    ('OI007', 'O003', 'P005', 1, 120.00, '2025-01-15 10:00:00'),
    ('OI008', 'O003', 'P006', 1, 75.00, '2025-01-15 10:00:00'),
    ('OI009', 'O004', 'P007', 1, 150.00, '2025-01-18 17:00:00'),
    ('OI010', 'O005', 'P008', 1, 15.00, '2025-01-20 12:00:00'),
    ('OI011', 'O005', 'P001', 1, 25.00, '2025-01-20 12:00:00'),
    ('OI012', 'O006', 'P002', 2, 89.00, '2025-01-22 09:00:00'),
    ('OI013', 'O006', 'P007', 1, 120.00, '2025-01-22 09:00:00'),
    ('OI014', 'O006', 'P003', 1, 12.00, '2025-01-22 09:00:00'),
    ('OI015', 'O007', 'P002', 1, 89.00, '2025-01-25 14:00:00'),
    ('OI016', 'O008', 'P007', 1, 150.00, '2025-02-01 11:00:00')
ON CONFLICT (order_item_id) DO NOTHING;

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_order_date ON orders(order_date);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);
CREATE INDEX IF NOT EXISTS idx_customers_tier ON customers(customer_tier);

-- Grant permissions to dbt_user
GRANT SELECT ON ALL TABLES IN SCHEMA public TO dbt_user;
GRANT USAGE ON SCHEMA public TO dbt_user;
