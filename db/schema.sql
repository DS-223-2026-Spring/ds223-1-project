CREATE TABLE IF NOT EXISTS customers (
  customer_id SERIAL PRIMARY KEY,
  segment_label VARCHAR(30),
  recency FLOAT NOT NULL,
  frequency FLOAT NOT NULL,
  monetary FLOAT NOT NULL,
  basket_diversity FLOAT,
  avg_order_size FLOAT,
  purchase_regularity FLOAT,
  created_at TIMESTAMP DEFAULT now()
);


CREATE TABLE IF NOT EXISTS raw_transactions (
  transaction_id SERIAL PRIMARY KEY,
  customer_id INTEGER REFERENCES customers(customer_id),
  invoice_no VARCHAR(20) NOT NULL,
  stock_code VARCHAR(20),
  description TEXT,
  quantity INTEGER,
  invoice_date TIMESTAMP,
  unit_price FLOAT,
  country VARCHAR(50),
  line_total FLOAT GENERATED ALWAYS AS (quantity * unit_price) STORED
);


CREATE TABLE IF NOT EXISTS actions (
  action_id SERIAL PRIMARY KEY,
  action_name VARCHAR(50) UNIQUE NOT NULL,
  action_cost FLOAT NOT NULL DEFAULT 0.0,
  description TEXT
);


CREATE TABLE IF NOT EXISTS simulations (
  simulation_id SERIAL PRIMARY KEY,
  sim_name VARCHAR(100),
  num_rounds INTEGER,
  num_customers INTEGER,
  alpha FLOAT DEFAULT 0.5,
  notes TEXT,
  started_at TIMESTAMP DEFAULT now(),
  completed_at TIMESTAMP
);


CREATE TABLE IF NOT EXISTS interactions (
  interaction_id SERIAL PRIMARY KEY,
  customer_id INTEGER REFERENCES customers(customer_id),
  action_id INTEGER REFERENCES actions(action_id),
  simulation_id INTEGER REFERENCES simulations(simulation_id),
  reward FLOAT,
  converted BOOLEAN,
  revenue FLOAT,
  cost FLOAT,
  round_number INTEGER,
  created_at TIMESTAMP DEFAULT now()
);


CREATE TABLE IF NOT EXISTS model_state (
  state_id SERIAL PRIMARY KEY,
  action_id INTEGER REFERENCES actions(action_id),
  theta_vector BYTEA,
  a_matrix BYTEA,
  b_vector BYTEA,
  alpha FLOAT DEFAULT 0.5,
  updated_at TIMESTAMP DEFAULT now()
);