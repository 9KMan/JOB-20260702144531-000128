-- ============================================================
-- Multi-tenant SaaS Sample Database
-- Day 1: Understand the data model
-- ============================================================

USE multitenant_saas;

-- Companies (tenants)
CREATE TABLE companies (
    company_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    domain VARCHAR(100) NOT NULL,
    plan ENUM('starter', 'professional', 'enterprise') DEFAULT 'starter',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Users (per company, per access level)
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    role ENUM('executive', 'manager', 'analyst', 'viewer') NOT NULL,
    business_unit VARCHAR(100),  -- e.g., 'Sales', 'Marketing', 'Engineering'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

-- Sales data (per company)
CREATE TABLE sales (
    sale_id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    business_unit VARCHAR(100) NOT NULL,
    region VARCHAR(50) NOT NULL,
    product VARCHAR(100) NOT NULL,
    amount DECIMAL(12, 2) NOT NULL,
    sale_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

-- ============================================================
-- Sample Data: 2 Tenants
-- ============================================================

-- Tenant 1: Acme Corp (enterprise plan, 3 users)
INSERT INTO companies (name, domain, plan) VALUES 
    ('Acme Corporation', 'acme.com', 'enterprise');

INSERT INTO users (company_id, email, full_name, role, business_unit) VALUES
    (1, 'ceo@acme.com', 'Alice Executive', 'executive', NULL),          -- sees ALL data
    (1, 'sales_mgr@acme.com', 'Bob Manager', 'manager', 'Sales'),         -- sees Sales only
    (1, 'analyst@acme.com', 'Carol Analyst', 'analyst', 'Sales');         -- sees Sales data

INSERT INTO sales (company_id, business_unit, region, product, amount, sale_date) VALUES
    (1, 'Sales', 'North', 'Widget Pro', 50000.00, '2025-01-15'),
    (1, 'Sales', 'South', 'Widget Basic', 32000.00, '2025-01-20'),
    (1, 'Sales', 'East', 'Widget Pro', 48000.00, '2025-02-01'),
    (1, 'Marketing', 'North', 'Ad Campaign', 12000.00, '2025-01-10'),
    (1, 'Marketing', 'South', 'Ad Campaign', 8500.00, '2025-01-25'),
    (1, 'Engineering', 'West', 'Support Contract', 22000.00, '2025-02-05');

-- Tenant 2: TechStart Inc (professional plan, 2 users)
INSERT INTO companies (name, domain, plan) VALUES 
    ('TechStart Inc', 'techstart.io', 'professional');

INSERT INTO users (company_id, email, full_name, role, business_unit) VALUES
    (2, 'founder@techstart.io', 'Dan Founder', 'executive', NULL),       -- sees ALL data
    (2, 'dev@techstart.io', 'Eve Developer', 'analyst', 'Engineering');  -- sees Engineering only

INSERT INTO sales (company_id, business_unit, region, product, amount, sale_date) VALUES
    (2, 'Engineering', 'North', 'SaaS License', 18000.00, '2025-01-12'),
    (2, 'Engineering', 'South', 'Support Contract', 9500.00, '2025-01-28'),
    (2, 'Sales', 'East', 'Consulting', 28000.00, '2025-02-03'),
    (2, 'Sales', 'West', 'SaaS License', 35000.00, '2025-02-10');
