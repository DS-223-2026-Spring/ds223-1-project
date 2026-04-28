# Initial EDA Report

- Simulation ID: `synthetic_seed42_cust500_rounds5000`
- Customers: 500
- Interactions: 5000
- Distinct simulations: 1
- Latent table available: yes

## Segment Mix
- Champion: 87 customers
- Loyal: 212 customers
- At-Risk: 63 customers
- Lost: 138 customers

## Topline Findings
- Highest mean conversion: `product_recommendation` (0.324)
- Highest mean reward: `bundle_offer` (33.24)
- Mean avg order size: 64.44; mean monetary value: 374.93

## Output Artifacts
- Summary CSVs: `segment_counts.csv`, `customer_summary.csv`, `segment_feature_means.csv`, `action_summary.csv`, `feature_correlations.csv`
- Plots: `segment_counts.png`, `customer_feature_histograms.png`, `segment_scatter.png`, `action_performance.png`, `action_reward_distribution.png`, `feature_correlations.png`
- Additional latent-aware outputs: `latent_feature_correlations.csv`, `latent_feature_correlations.png`
