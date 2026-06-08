-- Multi-tenant database initialization
-- Organizations → Tenants → Users model

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Organizations
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Tenants (one per org in this simple model)
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    db_schema VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(org_id, db_schema)
);

-- Departments
CREATE TABLE departments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    dept_id UUID REFERENCES departments(id),
    role VARCHAR(50) DEFAULT 'viewer',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Sample Sales data per tenant
CREATE TABLE sales (
    id SERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    sale_date DATE NOT NULL,
    product VARCHAR(255),
    amount DECIMAL(12,2),
    quantity INTEGER,
    region VARCHAR(100)
);

-- Insert sample tenants
INSERT INTO organizations (id, name, slug) VALUES
    ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'Acme Corp', 'acme'),
    ('b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22', 'Beta Inc', 'beta');

INSERT INTO tenants (id, org_id, name, db_schema) VALUES
    ('c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a33', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'Acme Corp Sales', 'acme_sales'),
    ('d0eebc99-9c0b-4ef8-bb6d-6bb9bd380a44', 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22', 'Beta Inc Sales', 'beta_sales');

INSERT INTO departments (id, tenant_id, name) VALUES
    ('e0eebc99-9c0b-4ef8-bb6d-6bb9bd380a55', 'c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a33', 'Sales'),
    ('f0eebc99-9c0b-4ef8-bb6d-6bb9bd380a66', 'd0eebc99-9c0b-4ef8-bb6d-6bb9bd380a44', 'Sales');

-- Sample data for Acme
INSERT INTO sales (tenant_id, sale_date, product, amount, quantity, region) VALUES
    ('c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a33', '2024-01-15', 'Widget A', 1000.00, 10, 'North'),
    ('c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a33', '2024-01-20', 'Widget B', 2500.00, 5, 'South'),
    ('c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a33', '2024-02-01', 'Widget A', 1500.00, 15, 'North');

-- Sample data for Beta
INSERT INTO sales (tenant_id, sale_date, product, amount, quantity, region) VALUES
    ('d0eebc99-9c0b-4ef8-bb6d-6bb9bd380a44', '2024-01-15', 'Gadget X', 3000.00, 20, 'East'),
    ('d0eebc99-9c0b-4ef8-bb6d-6bb9bd380a44', '2024-01-25', 'Gadget Y', 1800.00, 12, 'West');

-- Create RLS policies (PostgreSQL row-level security)
ALTER TABLE sales ENABLE ROW LEVEL SECURITY;

CREATE POLICY sales_tenant_isolation ON sales
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID);

-- Function to set tenant context
CREATE OR REPLACE FUNCTION set_tenant_context(p_tenant_id UUID)
RETURNS VOID AS $$
BEGIN
    PERFORM set_config('app.current_tenant_id', p_tenant_id::TEXT, false);
END;
$$ LANGUAGE plpgsql;

GRANT ALL ON organizations, tenants, departments, users, sales TO superset;
