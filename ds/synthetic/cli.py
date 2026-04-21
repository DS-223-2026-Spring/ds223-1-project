"""CLI for standalone synthetic data generation."""

from __future__ import annotations

import argparse
from pathlib import Path

from .config import SUPPORTED_POLICY_MODES, SyntheticDataConfig
from .dbio import persist_pipeline_artifacts_to_db
from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""

    parser = argparse.ArgumentParser(
        description="Generate standalone synthetic retail personalization data."
    )
    parser.add_argument("--n-customers", type=int, default=500)
    parser.add_argument("--n-rounds", type=int, default=5000)
    parser.add_argument("--random-seed", type=int, default=42)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/synthetic_data"),
    )
    parser.add_argument("--simulation-id", type=str, default=None)
    parser.add_argument(
        "--policy-mode",
        choices=sorted(SUPPORTED_POLICY_MODES),
        default="random_policy",
    )
    parser.add_argument("--alpha", type=float, default=0.5)
    parser.add_argument(
        "--persist-db",
        action="store_true",
        help="Persist generated artifacts into PostgreSQL via db_interactions.",
    )
    parser.add_argument(
        "--db-notes",
        type=str,
        default=None,
        help="Optional notes stored with the created simulation record.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the generator and print a concise summary."""

    parser = build_parser()
    args = parser.parse_args(argv)

    config = SyntheticDataConfig(
        n_customers=args.n_customers,
        n_rounds=args.n_rounds,
        random_seed=args.random_seed,
        output_dir=args.output_dir,
        simulation_id=args.simulation_id,
        policy_mode=args.policy_mode,
        alpha=args.alpha,
    )

    artifacts = run_pipeline(config)
    if args.persist_db:
        result = persist_pipeline_artifacts_to_db(
            artifacts=artifacts,
            config=config,
            notes=args.db_notes,
        )
        print(
            "Persisted to DB: "
            f"simulation_id={result.simulation_id}, "
            f"customers={result.customers_inserted}, "
            f"interactions={result.interactions_inserted}, "
            f"model_state_rows={result.model_state_rows_upserted}"
        )
    print(artifacts.validation.report_text)
    print("")
    print(f"Artifacts written to: {config.output_dir}")
    return 0
