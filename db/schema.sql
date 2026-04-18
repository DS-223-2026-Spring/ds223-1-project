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

CREATE INDEX IF NOT EXISTS idx_interactions_sim ON interactions(simulation_id);
CREATE INDEX IF NOT EXISTS idx_interactions_customer ON interactions(customer_id);