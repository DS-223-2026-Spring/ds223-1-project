CREATE OR REPLACE FUNCTION sp_upsert_customer(
    p_customer_id INTEGER,
    p_gender VARCHAR,
    p_segment_label VARCHAR,
    p_recency DOUBLE PRECISION,
    p_frequency DOUBLE PRECISION,
    p_monetary NUMERIC,
    p_basket_diversity DOUBLE PRECISION,
    p_avg_order_size DOUBLE PRECISION,
    p_purchase_regularity DOUBLE PRECISION,
    p_z_price_sensitivity DOUBLE PRECISION,
    p_z_brand_loyalty DOUBLE PRECISION,
    p_z_impulse_tendency DOUBLE PRECISION
)
RETURNS INTEGER AS $$
DECLARE
    v_customer_id INTEGER;
BEGIN
    -- INSERT
    IF p_customer_id IS NULL THEN
        INSERT INTO customers (
            gender,
            segment_label,
            recency,
            frequency,
            monetary,
            basket_diversity,
            avg_order_size,
            purchase_regularity
        )
        VALUES (
            p_gender,
            p_segment_label,
            p_recency,
            p_frequency,
            p_monetary,
            p_basket_diversity,
            p_avg_order_size,
            p_purchase_regularity
        )
        RETURNING customer_id INTO v_customer_id;

    -- UPDATE
    ELSE
        UPDATE customers
        SET
            gender = COALESCE(p_gender, gender),
            segment_label = COALESCE(p_segment_label, segment_label),
            recency = COALESCE(p_recency, recency),
            frequency = COALESCE(p_frequency, frequency),
            monetary = COALESCE(p_monetary, monetary),
            basket_diversity = COALESCE(p_basket_diversity, basket_diversity),
            avg_order_size = COALESCE(p_avg_order_size, avg_order_size),
            purchase_regularity = COALESCE(p_purchase_regularity, purchase_regularity)
        WHERE customer_id = p_customer_id
        RETURNING customer_id INTO v_customer_id;

        IF v_customer_id IS NULL THEN
            RAISE EXCEPTION 'Customer % not found', p_customer_id;
        END IF;
    END IF;

    -- LATENTS UPSERT
    IF p_z_price_sensitivity IS NOT NULL THEN
        INSERT INTO customer_latents (
            customer_id,
            z_price_sensitivity,
            z_brand_loyalty,
            z_impulse_tendency
        )
        VALUES (
            v_customer_id,
            p_z_price_sensitivity,
            p_z_brand_loyalty,
            p_z_impulse_tendency
        )
        ON CONFLICT (customer_id) DO UPDATE
        SET
            z_price_sensitivity = EXCLUDED.z_price_sensitivity,
            z_brand_loyalty = EXCLUDED.z_brand_loyalty,
            z_impulse_tendency = EXCLUDED.z_impulse_tendency;
    END IF;

    RETURN v_customer_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION sp_log_interaction(
    p_simulation_id INT,
    p_customer_id INT,
    p_action_id INT,
    p_round_number INT,
    p_context BYTEA,
    p_ucb_score DOUBLE PRECISION,
    p_cost NUMERIC
)
RETURNS INTEGER AS $$
DECLARE
    v_cost NUMERIC;
    v_interaction_id INT;
BEGIN
    -- Validate existence (optional but clearer errors)
    IF NOT EXISTS (SELECT 1 FROM simulations WHERE simulation_id = p_simulation_id) THEN
        RAISE EXCEPTION 'Simulation % does not exist', p_simulation_id;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM customers WHERE customer_id = p_customer_id) THEN
        RAISE EXCEPTION 'Customer % does not exist', p_customer_id;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM actions WHERE action_id = p_action_id) THEN
        RAISE EXCEPTION 'Action % does not exist', p_action_id;
    END IF;

    -- Cost fallback
    IF p_cost IS NULL THEN
        SELECT action_cost INTO v_cost
        FROM actions
        WHERE action_id = p_action_id;
    ELSE
        v_cost := p_cost;
    END IF;

    -- Insert interaction
    INSERT INTO interactions (
        simulation_id,
        customer_id,
        action_id,
        round_number,
        context_vector,
        ucb_score,
        cost
    )
    VALUES (
        p_simulation_id,
        p_customer_id,
        p_action_id,
        p_round_number,
        p_context,
        p_ucb_score,
        COALESCE(v_cost, 0.0)
    )
    RETURNING interaction_id INTO v_interaction_id;

    RETURN v_interaction_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION sp_submit_feedback(
    p_interaction_id INT,
    p_converted BOOLEAN,
    p_revenue NUMERIC,
    p_converted_at TIMESTAMPTZ,
    p_observed_at TIMESTAMPTZ
)
RETURNS TABLE (
    interaction_id INT,
    converted BOOLEAN,
    revenue NUMERIC,
    reward NUMERIC,
    observed_at TIMESTAMP
) AS $$
BEGIN
    -- Ensure interaction exists
    IF NOT EXISTS (
    SELECT 1
    FROM interactions i
    WHERE i.interaction_id = p_interaction_id
)THEN
        RAISE EXCEPTION 'Interaction % not found', p_interaction_id;
    END IF;

    -- Update
    UPDATE interactions
    SET
        converted = p_converted,
        revenue = COALESCE(p_revenue, 0.0),
        converted_at = CASE WHEN p_converted THEN p_converted_at ELSE NULL END,
        observed_at = COALESCE(p_observed_at, CURRENT_TIMESTAMP)
    WHERE interaction_id = p_interaction_id;

    -- Return updated row
    RETURN QUERY
    SELECT
        i.interaction_id,
        i.converted,
        i.revenue,
        i.reward,
        i.observed_at
    FROM interactions i
    WHERE i.interaction_id = p_interaction_id;
END;
$$ LANGUAGE plpgsql;