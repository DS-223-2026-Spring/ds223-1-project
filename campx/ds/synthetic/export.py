"""CSV and metadata export for the synthetic dataset pipeline."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .config import SyntheticDataConfig
from .validate import ValidationArtifacts, sanity_checks_to_json


def export_artifacts(
    output_dir: Path,
    config: SyntheticDataConfig,
    customers,
    customer_latents,
    actions,
    interactions,
    model_state,
    validation: ValidationArtifacts,
) -> None:
    """Write all required dataset and reporting artifacts to disk."""

    output_dir.mkdir(parents=True, exist_ok=True)

    customers.to_csv(output_dir / "customers.csv", index=False)
    customer_latents.to_csv(output_dir / "customer_latents.csv", index=False)
    actions.to_csv(output_dir / "actions.csv", index=False)
    interactions.to_csv(output_dir / "interactions.csv", index=False)
    model_state.to_csv(output_dir / "model_state.csv", index=False)

    try:
        from ..final_outputs import build_final_outputs
    except ImportError:  # pragma: no cover - supports running inside the ds container
        from final_outputs import build_final_outputs

    build_final_outputs(
        customers=customers,
        actions=actions,
        model_state=model_state,
        output_dir=output_dir,
    )

    validation.segment_counts.to_csv(output_dir / "segment_counts.csv", index=False)
    validation.action_summary.to_csv(output_dir / "action_summary.csv", index=False)
    validation.customer_summary.to_csv(output_dir / "customer_feature_summary.csv")
    validation.latent_feature_correlations.to_csv(
        output_dir / "latent_feature_correlations.csv"
    )
    validation.target_moment_comparison.to_csv(
        output_dir / "target_moment_comparison.csv",
        index=False,
    )
    validation.monotonicity_checks.to_csv(
        output_dir / "monotonicity_checks.csv",
        index=False,
    )
    (output_dir / "validation_report.txt").write_text(validation.report_text + "\n")
    (output_dir / "sanity_checks.json").write_text(
        sanity_checks_to_json(validation.sanity_checks) + "\n"
    )

    metadata = {
        "simulation_id": config.simulation_id,
        "policy_mode": config.policy_mode,
        "n_customers": config.n_customers,
        "n_rounds": config.n_rounds,
        "random_seed": config.random_seed,
        "alpha": config.alpha,
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (output_dir / "calibration.json").write_text(
        json.dumps(asdict(config.calibration), indent=2) + "\n"
    )
