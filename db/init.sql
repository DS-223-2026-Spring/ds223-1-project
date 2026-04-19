-- Campaign Optimization Engine | Schema
-- This script runs automatically on first container start

CREATE TABLE IF NOT EXISTS customers (
    customer_id SERIAL PRIMARY KEY,
    gender VARCHAR(16),
    segment_label VARCHAR(32) NOT NULL,
    recency INTEGER NOT NULL,
    frequency INTEGER NOT NULL,
    monetary DOUBLE PRECISION NOT NULL,
    basket_diversity DOUBLE PRECISION NOT NULL,
    avg_order_size DOUBLE PRECISION NOT NULL,
    purchase_regularity DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS customer_latents (
    customer_id INTEGER PRIMARY KEY REFERENCES customers(customer_id) ON DELETE CASCADE,
    z_price_sensitivity DOUBLE PRECISION NOT NULL,
    z_brand_loyalty DOUBLE PRECISION NOT NULL,
    z_impulse_tendency DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS actions (
    action_id INTEGER PRIMARY KEY,
    action_name VARCHAR(64) NOT NULL UNIQUE,
    action_cost DOUBLE PRECISION NOT NULL,
    description TEXT
);

INSERT INTO actions (action_id, action_name, action_cost, description) VALUES
    (0, 'no_action', 0.00, 'Control group; rely on organic conversion from loyal customers.'),
    (1, 'discount_10', 6.50, '10% discount for price-sensitive customers; margin-reducing but effective.'),
    (2, 'free_shipping', 4.99, 'Shipping-friction relief for planning-oriented shoppers.'),
    (3, 'product_recommendation', 0.30, 'Low-cost personalization that works best for loyal engaged shoppers.'),
    (4, 'bundle_offer', 9.00, 'Higher-basket bundle promotion for impulse-prone customers.')
ON CONFLICT (action_id) DO UPDATE SET
    action_name = EXCLUDED.action_name,
    action_cost = EXCLUDED.action_cost,
    description = EXCLUDED.description;

CREATE TABLE IF NOT EXISTS simulations (
    simulation_id SERIAL PRIMARY KEY,
    sim_name VARCHAR(128) NOT NULL,
    num_rounds INTEGER NOT NULL,
    num_customers INTEGER NOT NULL,
    alpha DOUBLE PRECISION NOT NULL,
    context_dim INTEGER NOT NULL DEFAULT 6,
    conversion_window_hours INTEGER NOT NULL DEFAULT 48,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS interactions (
    interaction_id SERIAL PRIMARY KEY,
    simulation_id INTEGER NOT NULL REFERENCES simulations(simulation_id) ON DELETE CASCADE,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    action_id INTEGER NOT NULL REFERENCES actions(action_id),
    round_number INTEGER NOT NULL,
    context_vector BYTEA,
    ucb_score DOUBLE PRECISION,
    cost DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    converted BOOLEAN,
    revenue DOUBLE PRECISION,
    reward DOUBLE PRECISION,
    decision_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    converted_at TIMESTAMP,
    observed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS model_state (
    model_state_id SERIAL PRIMARY KEY,
    simulation_id INTEGER NOT NULL REFERENCES simulations(simulation_id) ON DELETE CASCADE,
    action_id INTEGER NOT NULL REFERENCES actions(action_id),
    round_number INTEGER NOT NULL DEFAULT 0,
    n_pulls INTEGER NOT NULL DEFAULT 0,
    theta_bytes BYTEA NOT NULL,
    a_bytes BYTEA NOT NULL,
    b_bytes BYTEA NOT NULL,
    alpha DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (simulation_id, action_id)
);

CREATE INDEX IF NOT EXISTS idx_customers_segment_label
    ON customers(segment_label);

CREATE INDEX IF NOT EXISTS idx_interactions_simulation_round
    ON interactions(simulation_id, round_number);

CREATE INDEX IF NOT EXISTS idx_interactions_customer
    ON interactions(customer_id);

CREATE INDEX IF NOT EXISTS idx_interactions_pending
    ON interactions(observed_at, decision_at);

CREATE INDEX IF NOT EXISTS idx_model_state_sim_action
    ON model_state(simulation_id, action_id);
