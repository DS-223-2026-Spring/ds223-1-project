"""CLI for standalone synthetic data generation."""

from __future__ import annotations

import argparse
from pathlib import Path

from .config import SUPPORTED_POLICY_MODES, SyntheticDataConfig
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
    print(artifacts.validation.report_text)
    print("")
    print(f"Artifacts written to: {config.output_dir}")
    return 0
