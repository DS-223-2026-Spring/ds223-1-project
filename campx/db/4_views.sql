CREATE OR REPLACE VIEW view_customer_with_latents AS
SELECT
    c.customer_id,
    c.gender,
    c.segment_label,
    c.recency,
    c.frequency,
    c.monetary,
    c.basket_diversity,
    c.avg_order_size,
    c.purchase_regularity,
    c.created_at,
    l.z_price_sensitivity,
    l.z_brand_loyalty,
    l.z_impulse_tendency
FROM public.customers AS c
LEFT JOIN public.customer_latents AS l
    ON l.customer_id = c.customer_id;


CREATE OR REPLACE VIEW view_simulation_summary AS
SELECT
    s.simulation_id,
    s.sim_name,
    s.num_rounds,
    s.num_customers,
    s.alpha,
    s.context_dim,
    s.conversion_window_hours,
    s.notes,
    s.started_at,
    s.completed_at,
    CASE
        WHEN s.completed_at IS NOT NULL THEN 'completed'
        ELSE 'running'
    END AS status,
    COUNT(i.interaction_id)::int AS rounds_completed,
    CASE
        WHEN COUNT(*) FILTER (WHERE i.observed_at IS NOT NULL) = 0 THEN NULL
        ELSE COALESCE(SUM(i.reward) FILTER (WHERE i.observed_at IS NOT NULL), 0.0)
    END AS cumulative_reward
FROM public.simulations AS s
LEFT JOIN public.interactions AS i
    ON i.simulation_id = s.simulation_id
GROUP BY
    s.simulation_id,
    s.sim_name,
    s.num_rounds,
    s.num_customers,
    s.alpha,
    s.context_dim,
    s.conversion_window_hours,
    s.notes,
    s.started_at,
    s.completed_at;