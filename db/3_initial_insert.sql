INSERT INTO actions (action_id, action_name, action_cost, target_latent, description)
OVERRIDING SYSTEM VALUE VALUES
    (0, 'no_action',     0.00, 'brand_loyalty',              'Control — no promotion sent. Protects margin for loyal customers who buy regardless.'),
    (1, 'discount_10',   6.50, 'price_sensitivity',          '10% off next order. Brand absorbs avg £6.50. Targets price-sensitive lapsed customers.'),
    (2, 'free_shipping', 4.99, 'price_sensitivity+planning', 'Standard shipping waived. Removes friction for moderate-basket planners.'),
    (3, 'product_recommendation', 0.30, 'brand_loyalty+impulse', 'Personalised category suggestion email. Highest-margin action when it converts.'),
    (4, 'bundle_offer',  9.00, 'impulse_tendency',           'Curated outfit at 15% off. Increases basket value. Works on impulse buyers.');

INSERT INTO products (product_name, category, gender, price, margin_pct) VALUES
    ('Slim-fit chinos',              'bottoms',    'M',      59.99, 0.62),
    ('Oxford button-down shirt',     'tops',       'M',      45.99, 0.60),
    ('Wool overcoat',                'outerwear',  'M',     119.99, 0.65),
    ('Leather belt',                 'accessories','M',      29.99, 0.70),
    ('Derby shoes',                  'shoes',      'M',      89.99, 0.58),
    ('Ribbed knit top',              'tops',       'F',      34.99, 0.63),
    ('High-waist wide-leg trousers', 'bottoms',    'F',      54.99, 0.61),
    ('Oversized blazer',             'outerwear',  'F',      89.99, 0.64),
    ('Crossbody bag',                'accessories','F',      49.99, 0.68),
    ('Block-heel ankle boots',       'shoes',      'F',      79.99, 0.59),
    ('White crew-neck tee',          'tops',       'unisex', 19.99, 0.65),
    ('Canvas tote bag',              'accessories','unisex', 24.99, 0.72);

INSERT INTO bundles (bundle_name, gender, product_1_id, product_2_id, product_3_id, full_price, bundle_price, saving) VALUES
    ('The Weekend Look',   'M', 1, 2, 4,    135.97, 115.57, 20.40),
    ('Office Essentials',  'M', 1, 2, NULL, 105.98,  90.08, 15.90),
    ('Winter Edit Men',    'M', 3, 1, NULL, 179.98, 152.98, 27.00),
    ('The Day Look',       'F', 6, 7, 9,    139.97, 118.97, 21.00),
    ('Smart Casual',       'F', 8, 7, NULL, 144.98, 123.23, 21.75),
    ('Winter Edit Women',  'F', 8, 10, NULL,169.98, 144.48, 25.50);
