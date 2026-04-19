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
        sanity_checks=sanity_checks,
    )

    return ValidationArtifacts(
        segment_counts=segment_counts,
        action_summary=action_summary,
        customer_summary=customer_summary,
        latent_feature_correlations=latent_feature_correlations,
        sanity_checks=sanity_checks,
        report_text=report_text,
    )


def sanity_checks_to_json(sanity_checks: dict[str, object]) -> str:
    """Serialize sanity checks for file export."""

    return json.dumps(sanity_checks, indent=2, sort_keys=True)


def _format_report(
    config: SyntheticDataConfig,
    segment_counts: pd.DataFrame,
    action_summary: pd.DataFrame,
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

    return "\n".join(lines)
