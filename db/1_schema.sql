CREATE TABLE IF NOT EXISTS customers (
    customer_id          SERIAL PRIMARY KEY,
    gender               VARCHAR(1)  NOT NULL CHECK (gender IN ('M','F')),
    segment_label        VARCHAR(20) NOT NULL CHECK (segment_label IN ('Champion','Loyal','At-Risk','Lost')),
    recency              DOUBLE PRECISION NOT NULL,
    frequency            DOUBLE PRECISION NOT NULL,
    monetary             NUMERIC(12,2)    NOT NULL,
    basket_diversity     DOUBLE PRECISION NOT NULL,
    avg_order_size       DOUBLE PRECISION NOT NULL,
    purchase_regularity  DOUBLE PRECISION NOT NULL,
    created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS customer_latents (
    customer_id          INTEGER PRIMARY KEY
                         REFERENCES customers(customer_id) ON DELETE CASCADE,
    z_price_sensitivity  DOUBLE PRECISION NOT NULL,
    z_brand_loyalty      DOUBLE PRECISION NOT NULL,
    z_impulse_tendency   DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    product_id    SERIAL PRIMARY KEY,
    product_name  VARCHAR(100) NOT NULL,
    category      VARCHAR(50)  NOT NULL,
    gender        VARCHAR(10)  NOT NULL CHECK (gender IN ('M','F','unisex')),
    price         NUMERIC(10,2) NOT NULL,
    margin_pct    NUMERIC(5,2)  NOT NULL CHECK (margin_pct >= 0 AND margin_pct <= 1)
);

CREATE TABLE IF NOT EXISTS bundles (
    bundle_id     SERIAL PRIMARY KEY,
    bundle_name   VARCHAR(100) NOT NULL,
    gender        VARCHAR(10)  NOT NULL CHECK (gender IN ('M','F','unisex')),
    product_1_id  INTEGER NOT NULL REFERENCES products(product_id),
    product_2_id  INTEGER NOT NULL REFERENCES products(product_id),
    product_3_id  INTEGER     REFERENCES products(product_id),
    full_price    NUMERIC(10,2) NOT NULL,
    bundle_price  NUMERIC(10,2) NOT NULL,
    saving        NUMERIC(10,2) NOT NULL,
    CHECK (product_1_id <> product_2_id),
    CHECK (product_3_id IS NULL OR product_3_id NOT IN (product_1_id, product_2_id))
);

CREATE TABLE IF NOT EXISTS actions (
    action_id      SERIAL PRIMARY KEY,
    action_name    VARCHAR(50) NOT NULL UNIQUE,
    action_cost    NUMERIC(10,2) NOT NULL DEFAULT 0.0,
    target_latent  VARCHAR(50) NOT NULL,
    description    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS simulations (
    simulation_id           SERIAL PRIMARY KEY,
    sim_name                VARCHAR(100) NOT NULL,

    num_rounds              INTEGER NOT NULL,
    num_customers           INTEGER NOT NULL,

    alpha                   DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    context_dim             INTEGER NOT NULL DEFAULT 6,
    conversion_window_hours INTEGER NOT NULL DEFAULT 48,

    notes                   TEXT,

    started_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at            TIMESTAMP
);

CREATE TABLE IF NOT EXISTS interactions (
    interaction_id  SERIAL PRIMARY KEY,
    simulation_id   INTEGER NOT NULL
                    REFERENCES simulations(simulation_id) ON DELETE CASCADE,
    customer_id     INTEGER NOT NULL
                    REFERENCES customers(customer_id) ON DELETE CASCADE,
    action_id       INTEGER NOT NULL
                    REFERENCES actions(action_id),
    round_number    INTEGER NOT NULL,
    decision_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    converted_at    TIMESTAMP,
    observed_at     TIMESTAMP,
    context_vector  BYTEA NOT NULL,
    ucb_score       DOUBLE PRECISION NOT NULL,
    converted       BOOLEAN,
    revenue         NUMERIC(12,2) NOT NULL DEFAULT 0.0,
    cost            NUMERIC(12,2) NOT NULL,
    reward          NUMERIC(12,2),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CHECK (observed_at IS NOT NULL OR converted IS NULL)
);

CREATE TABLE IF NOT EXISTS model_state (
    state_id       SERIAL PRIMARY KEY,
    simulation_id  INTEGER NOT NULL
                   REFERENCES simulations(simulation_id) ON DELETE CASCADE,
    action_id      INTEGER NOT NULL
                   REFERENCES actions(action_id),
    round_number   INTEGER NOT NULL,
    n_pulls        INTEGER NOT NULL DEFAULT 0,
    theta_vector   BYTEA NOT NULL,
    a_matrix       BYTEA NOT NULL,
    b_vector       BYTEA NOT NULL,
    alpha          DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);