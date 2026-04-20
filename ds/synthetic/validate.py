"""Validation and summary reporting for synthetic dataset generation."""

from __future__ import annotations

import json
from dataclasses import dataclass

import pandas as pd

from .config import FEATURE_COLUMNS, LATENT_COLUMNS, SyntheticDataConfig


@dataclass(slots=True)
class ValidationArtifacts:
    """Structured validation outputs for export and terminal reporting."""

    segment_counts: pd.DataFrame
    action_summary: pd.DataFrame
    customer_summary: pd.DataFrame
    latent_feature_correlations: pd.DataFrame
    target_moment_comparison: pd.DataFrame
    monotonicity_checks: pd.DataFrame
    sanity_checks: dict[str, object]
    report_text: str


def build_validation_artifacts(
    customers: pd.DataFrame,
    latents: pd.DataFrame,
    actions: pd.DataFrame,
    interactions: pd.DataFrame,
    config: SyntheticDataConfig,
) -> ValidationArtifacts:
    """Build summary tables and sanity checks."""

    segment_counts = (
        customers["segment"]
        .value_counts()
        .rename_axis("segment")
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .reset_index(drop=True)
    )

    interaction_summary = interactions.merge(
        actions[["action_id", "action_name"]], on="action_id", how="left"
    )
    action_summary = (
        interaction_summary.groupby(["action_id", "action_name"], as_index=False)
        .agg(
            observations=("interaction_id", "count"),
            mean_conversion_rate=("converted", "mean"),
            mean_revenue=("revenue", "mean"),
            mean_cost=("cost", "mean"),
            mean_reward=("reward", "mean"),
            mean_p_convert=("p_convert", "mean"),
        )
        .round(
            {
                "mean_conversion_rate": 4,
                "mean_revenue": 2,
                "mean_cost": 2,
                "mean_reward": 2,
                "mean_p_convert": 4,
            }
        )
    )

    customer_summary = customers[FEATURE_COLUMNS].describe().round(3)

    merged = customers.merge(latents, on="customer_id", how="inner")
    latent_feature_correlations = (
        merged[LATENT_COLUMNS + FEATURE_COLUMNS]
        .corr()
        .loc[LATENT_COLUMNS, FEATURE_COLUMNS]
        .round(3)
    )

    target_moment_comparison = build_target_moment_comparison(
        customers=customers,
        interactions=interaction_summary,
        config=config,
    )
    monotonicity_checks = build_monotonicity_checks(
        customers=customers,
        latents=latents,
        interactions=interaction_summary,
        config=config,
    )

    bundle_avg_revenue = (
        interaction_summary.loc[interaction_summary["action_id"] == 4, "revenue"].mean()
    )
    no_action_avg_revenue = (
        interaction_summary.loc[interaction_summary["action_id"] == 0, "revenue"].mean()
    )
    sanity_checks = {
        "simulation_id": config.simulation_id,
        "policy_mode": config.policy_mode,
        "negative_recency_count": int((customers["recency"] < 0).sum()),
        "non_positive_frequency_count": int((customers["frequency"] <= 0).sum()),
        "negative_monetary_count": int((customers["monetary"] < 0).sum()),
        "avg_order_out_of_range_count": int(
            ((customers["avg_order_size"] < 15) | (customers["avg_order_size"] > 120)).sum()
        ),
        "invalid_probability_count": int(
            ((interactions["p_convert"] < 0) | (interactions["p_convert"] > 1)).sum()
        ),
        "negative_cost_count": int((interactions["cost"] < 0).sum()),
        "converted_with_zero_revenue_count": int(
            ((interactions["converted"]) & (interactions["revenue"] <= 0)).sum()
        ),
        "bundle_avg_revenue_gt_no_action_avg_revenue": bool(
            bundle_avg_revenue > no_action_avg_revenue
        ),
    }

    report_text = _format_report(
        config=config,
        segment_counts=segment_counts,
        action_summary=action_summary,
        target_moment_comparison=target_moment_comparison,
        monotonicity_checks=monotonicity_checks,
        sanity_checks=sanity_checks,
    )

    return ValidationArtifacts(
        segment_counts=segment_counts,
        action_summary=action_summary,
        customer_summary=customer_summary,
        latent_feature_correlations=latent_feature_correlations,
        target_moment_comparison=target_moment_comparison,
        monotonicity_checks=monotonicity_checks,
        sanity_checks=sanity_checks,
        report_text=report_text,
    )


def build_target_moment_comparison(
    customers: pd.DataFrame,
    interactions: pd.DataFrame,
    config: SyntheticDataConfig,
) -> pd.DataFrame:
    """Compare realized dataset moments against configured targets."""

    targets = config.calibration.targets
    rows: list[dict[str, object]] = []

    actual_segment_mix = customers["segment"].value_counts(normalize=True).to_dict()
    for segment_name, target_share in targets.segment_mix.items():
        actual_share = float(actual_segment_mix.get(segment_name, 0.0))
        deviation = actual_share - target_share
        rows.append(
            {
                "metric_group": "segment_mix",
                "metric_name": segment_name,
                "target": round(target_share, 4),
                "actual": round(actual_share, 4),
                "deviation": round(deviation, 4),
                "within_tolerance": abs(deviation) <= targets.segment_mix_tolerance,
            }
        )

    actual_mean_aov = float(customers["avg_order_size"].mean())
    rows.append(
        {
            "metric_group": "avg_order_size",
            "metric_name": "mean_avg_order_size",
            "target": round(targets.mean_avg_order_size, 4),
            "actual": round(actual_mean_aov, 4),
            "deviation": round(actual_mean_aov - targets.mean_avg_order_size, 4),
            "within_tolerance": abs(actual_mean_aov - targets.mean_avg_order_size)
            <= targets.mean_avg_order_tolerance,
        }
    )

    actual_conversion = interactions.groupby("action_name")["converted"].mean().to_dict()
    for action_name, target_rate in targets.conversion_rate_by_action.items():
        actual_rate = float(actual_conversion.get(action_name, 0.0))
        rows.append(
            {
                "metric_group": "conversion_rate",
                "metric_name": action_name,
                "target": round(target_rate, 4),
                "actual": round(actual_rate, 4),
                "deviation": round(actual_rate - target_rate, 4),
                "within_tolerance": abs(actual_rate - target_rate)
                <= targets.conversion_tolerance,
            }
        )

    converted_only = interactions.loc[interactions["converted"]].copy()
    converted_revenue = converted_only.groupby("action_name")["revenue"].mean().to_dict()
    for action_name, (range_min, range_max) in targets.converted_revenue_range_by_action.items():
        actual_revenue = float(converted_revenue.get(action_name, 0.0))
        midpoint = (range_min + range_max) / 2.0
        rows.append(
            {
                "metric_group": "converted_revenue_range",
                "metric_name": action_name,
                "target": round(midpoint, 4),
                "actual": round(actual_revenue, 4),
                "deviation": round(actual_revenue - midpoint, 4),
                "within_tolerance": range_min <= actual_revenue <= range_max,
            }
        )

    return pd.DataFrame(rows)


def build_monotonicity_checks(
    customers: pd.DataFrame,
    latents: pd.DataFrame,
    interactions: pd.DataFrame,
    config: SyntheticDataConfig,
) -> pd.DataFrame:
    """Verify the directional assumptions remain true after refactors."""

    monotonicity_cfg = config.calibration.monotonicity
    merged = customers.merge(latents, on="customer_id", how="inner")
    cutoff = monotonicity_cfg.quantile_cutoff

    low_loyalty = merged["z_brand_loyalty"] <= merged["z_brand_loyalty"].quantile(cutoff)
    high_loyalty = merged["z_brand_loyalty"] >= merged["z_brand_loyalty"].quantile(1.0 - cutoff)
    low_impulse = merged["z_impulse_tendency"] <= merged["z_impulse_tendency"].quantile(cutoff)
    high_impulse = merged["z_impulse_tendency"] >= merged["z_impulse_tendency"].quantile(1.0 - cutoff)
    low_price = merged["z_price_sensitivity"] <= merged["z_price_sensitivity"].quantile(cutoff)
    high_price = merged["z_price_sensitivity"] >= merged["z_price_sensitivity"].quantile(1.0 - cutoff)

    converted = interactions.loc[interactions["converted"]].copy()
    bundle_converted_revenue = float(
        converted.loc[converted["action_name"] == "bundle_offer", "revenue"].mean()
    )
    no_action_converted_revenue = float(
        converted.loc[converted["action_name"] == "no_action", "revenue"].mean()
    )

    rows = [
        _monotonicity_row(
            "high_loyalty_lowers_recency",
            float(merged.loc[low_loyalty, "recency"].mean() - merged.loc[high_loyalty, "recency"].mean()),
            monotonicity_cfg.loyalty_recency_gap_min,
        ),
        _monotonicity_row(
            "high_loyalty_raises_frequency",
            float(merged.loc[high_loyalty, "frequency"].mean() - merged.loc[low_loyalty, "frequency"].mean()),
            monotonicity_cfg.loyalty_frequency_gap_min,
        ),
        _monotonicity_row(
            "high_loyalty_raises_monetary",
            float(merged.loc[high_loyalty, "monetary"].mean() - merged.loc[low_loyalty, "monetary"].mean()),
            monotonicity_cfg.loyalty_monetary_gap_min,
        ),
        _monotonicity_row(
            "high_loyalty_raises_regularity",
            float(
                merged.loc[high_loyalty, "purchase_regularity"].mean()
                - merged.loc[low_loyalty, "purchase_regularity"].mean()
            ),
            monotonicity_cfg.loyalty_regularity_gap_min,
        ),
        _monotonicity_row(
            "high_impulse_raises_basket_diversity",
            float(
                merged.loc[high_impulse, "basket_diversity"].mean()
                - merged.loc[low_impulse, "basket_diversity"].mean()
            ),
            monotonicity_cfg.impulse_basket_gap_min,
        ),
        _monotonicity_row(
            "high_impulse_raises_avg_order_size",
            float(
                merged.loc[high_impulse, "avg_order_size"].mean()
                - merged.loc[low_impulse, "avg_order_size"].mean()
            ),
            monotonicity_cfg.impulse_avg_order_gap_min,
        ),
        _monotonicity_row(
            "low_price_sensitivity_raises_avg_order_size",
            float(
                merged.loc[low_price, "avg_order_size"].mean()
                - merged.loc[high_price, "avg_order_size"].mean()
            ),
            monotonicity_cfg.low_price_minus_high_price_aov_gap_min,
        ),
        _monotonicity_row(
            "bundle_offer_revenue_exceeds_no_action",
            float(bundle_converted_revenue - no_action_converted_revenue),
            monotonicity_cfg.bundle_minus_no_action_converted_revenue_gap_min,
        ),
    ]

    return pd.DataFrame(rows)


def sanity_checks_to_json(sanity_checks: dict[str, object]) -> str:
    """Serialize sanity checks for file export."""

    return json.dumps(sanity_checks, indent=2, sort_keys=True)


def _format_report(
    config: SyntheticDataConfig,
    segment_counts: pd.DataFrame,
    action_summary: pd.DataFrame,
    target_moment_comparison: pd.DataFrame,
    monotonicity_checks: pd.DataFrame,
    sanity_checks: dict[str, object],
) -> str:
    """Render a concise terminal report."""

    lines = [
        "Synthetic retail simulation report",
        f"simulation_id: {config.simulation_id}",
        f"policy_mode: {config.policy_mode}",
        f"n_customers: {config.n_customers}",
        f"n_rounds: {config.n_rounds}",
        "",
        "Segment counts:",
    ]

    for row in segment_counts.itertuples(index=False):
        lines.append(f"  - {row.segment}: {row.count}")

    lines.append("")
    lines.append("Mean conversion and reward by action:")
    for row in action_summary.itertuples(index=False):
        lines.append(
            "  - "
            f"{row.action_name}: conversion={row.mean_conversion_rate:.3f}, "
            f"reward={row.mean_reward:.2f}, observations={row.observations}"
        )

    lines.append("")
    lines.append("Sanity checks:")
    for key, value in sanity_checks.items():
        lines.append(f"  - {key}: {value}")

    lines.append("")
    lines.append(
        "Target moments within tolerance: "
        f"{int(target_moment_comparison['within_tolerance'].sum())}/"
        f"{len(target_moment_comparison)}"
    )
    lines.append(
        "Monotonicity checks passed: "
        f"{int(monotonicity_checks['passed'].sum())}/"
        f"{len(monotonicity_checks)}"
    )

    return "\n".join(lines)


def _monotonicity_row(metric_name: str, actual_gap: float, threshold: float) -> dict[str, object]:
    """Return one monotonicity check row."""

    return {
        "metric_name": metric_name,
        "actual_gap": round(actual_gap, 4),
        "threshold": round(threshold, 4),
        "passed": actual_gap >= threshold,
    }
