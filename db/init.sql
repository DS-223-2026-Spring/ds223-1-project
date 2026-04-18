-- Campaign Optimization Engine | Schema
-- This script runs automatically on first container start

CREATE TABLE IF NOT EXISTS customers (
    customer_id SERIAL PRIMARY KEY,
    recency FLOAT,
    frequency FLOAT,
    monetary FLOAT,
    basket_diversity FLOAT,
    avg_order_size FLOAT,
    purchase_regularity FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS actions (
    action_id SERIAL PRIMARY KEY,
    action_name VARCHAR(50) NOT NULL,
    action_cost FLOAT NOT NULL DEFAULT 0.0,
    description TEXT
);

-- Seed actions
INSERT INTO actions (action_name, action_cost, description) VALUES
    ('no_action', 0.0, 'Control — no promotion'),
    ('discount_10', 0.10, '10% discount offer'),
    ('free_shipping', 2.50, 'Free shipping offer'),
    ('product_recommendation', 0.05, 'Personalized product recommendation'),
    ('bundle_offer', 0.15, 'Cross-sell bundle at slight discount');

CREATE TABLE IF NOT EXISTS interactions (
    interaction_id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(customer_id),
    action_id INTEGER REFERENCES actions(action_id),
    reward FLOAT,
    converted BOOLEAN,
    revenue FLOAT,
    cost FLOAT,
    simulation_id VARCHAR(50),
    round_number INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS model_state (
    state_id SERIAL PRIMARY KEY,
    action_id INTEGER REFERENCES actions(action_id),
    theta_vector BYTEA,
    a_matrix BYTEA,
    b_vector BYTEA,
    alpha FLOAT DEFAULT 0.5,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_interactions_sim ON interactions(simulation_id);
CREATE INDEX IF NOT EXISTS idx_interactions_customer ON interactions(customer_id);


-- Simulation run metadata
CREATE TABLE IF NOT EXISTS simulations (
    simulation_id SERIAL PRIMARY KEY,
    sim_name VARCHAR(100),
    num_rounds INTEGER,
    num_customers INTEGER,
    alpha FLOAT DEFAULT 0.5,
    notes TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Raw source transactions (UCI Online Retail II)
CREATE TABLE IF NOT EXISTS raw_transactions (
    transaction_id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(customer_id),
    invoice_no VARCHAR(20),
    stock_code VARCHAR(20),
    description TEXT,
    quantity INTEGER,
    invoice_date TIMESTAMP,
    unit_price FLOAT,
    country VARCHAR(50),
    line_total FLOAT GENERATED ALWAYS AS (quantity * unit_price) STORED
);

-- Also add segment_label to customers (for Davit's EDA)
ALTER TABLE customers ADD COLUMN IF NOT EXISTS segment_label VARCHAR(30);

CREATE INDEX IF NOT EXISTS idx_raw_customer ON raw_transactions(customer_id);
CREATE INDEX IF NOT EXISTS idx_sim_name ON simulations(sim_name);