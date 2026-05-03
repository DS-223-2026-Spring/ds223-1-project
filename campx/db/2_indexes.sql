CREATE INDEX IF NOT EXISTS idx_interactions_simulation
    ON interactions(simulation_id);

CREATE INDEX IF NOT EXISTS idx_interactions_customer
    ON interactions(customer_id);

CREATE INDEX IF NOT EXISTS idx_interactions_decision_at
    ON interactions(decision_at);

CREATE INDEX IF NOT EXISTS idx_interactions_pending
    ON interactions(decision_at)
    WHERE observed_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_interactions_observed_at
    ON interactions(observed_at);

CREATE UNIQUE INDEX IF NOT EXISTS idx_simulations_name_unique
    ON simulations(sim_name);

CREATE INDEX IF NOT EXISTS idx_model_state_sim_action
    ON model_state(simulation_id, action_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_model_state_unique
    ON model_state(simulation_id, action_id, round_number);

CREATE INDEX IF NOT EXISTS idx_simulation_artifacts_simulation
    ON simulation_artifacts(simulation_id);