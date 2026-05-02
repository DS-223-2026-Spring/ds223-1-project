# Final DS Outputs

- Simulation ID: `synthetic_seed42_cust500_rounds5000`
- Policy mode: `linucb`
- Customers scored: 500
- Most common recommendation: `bundle_offer` for 302 customers
- Mean confidence score: 0.9278
- Mean top-vs-runner-up UCB margin: 7.4332

## Top Recommendation by Segment
- At-Risk: `bundle_offer` for 42 customers (66.7% of segment)
- Champion: `bundle_offer` for 43 customers (49.4% of segment)
- Lost: `bundle_offer` for 84 customers (60.9% of segment)
- Loyal: `bundle_offer` for 133 customers (62.7% of segment)

## Files
- `customer_recommendations.csv`: one final action per customer with segment, features, confidence, and UCB margin.
- `customer_action_scores.csv`: every customer-action score used to choose the recommendation.
- `recommendation_summary.csv`: segment-level recommendation mix and confidence summary.
- `eda/`: automatically generated EDA tables and plots for the same dataset.
