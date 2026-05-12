"""Repeatable command-line workflow for the full DS deliverable bundle."""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    from ._routing import import_ds_module, load_ds_attr
except ImportError:  # pragma: no cover - supports direct execution in DS container
    from _routing import import_ds_module, load_ds_attr

_config = import_ds_module("synthetic.config")
SUPPORTED_POLICY_MODES = _config.SUPPORTED_POLICY_MODES
SyntheticDataConfig = _config.SyntheticDataConfig
BaselineComparisonArtifacts = load_ds_attr("baselines", "BaselineComparisonArtifacts")
run_baseline_comparison = load_ds_attr("baselines", "run_baseline_comparison")
DatabasePersistenceResult = load_ds_attr("synthetic.dbio", "DatabasePersistenceResult")
persist_csv_artifacts_to_db = load_ds_attr("synthetic.dbio", "persist_csv_artifacts_to_db")
SyntheticArtifacts = load_ds_attr("synthetic.pipeline", "SyntheticArtifacts")
run_pipeline = load_ds_attr("synthetic.pipeline", "run_pipeline")

STORAGE_MODES = ("csv", "db", "both")


@dataclass(slots=True)
class WorkflowArtifacts:
    """Paths written by one repeatable DS workflow run."""

    output_dir: Path
    baseline_output_dir: Path | None
    manifest_path: Path
    report_path: Path
    db_result: DatabasePersistenceResult | None = None


@dataclass(frozen=True, slots=True)
class WorkflowConfig:
    """Runtime settings for the repeatable DS workflow."""

    n_customers: int = 500
    n_rounds: int = 5000
    random_seed: int = 42
    policy_mode: str = "linucb"
    alpha: float = 0.5
    output_dir: Path = Path("outputs/final_outputs")
    clean: bool = True
    run_baselines: bool = True
    baseline_n_customers: int = 500
    baseline_train_rounds: int = 5000
    baseline_eval_rounds: int = 5000
    baseline_output_dir: Path | None = None
    baseline_ridge_penalty: float = 5.0
    storage: str = "csv"
    db_notes: str | None = None


def run_workflow(config: WorkflowConfig) -> WorkflowArtifacts:
    """Run the deterministic DS pipeline and write a manifest."""

    if config.storage not in STORAGE_MODES:
        raise ValueError(f"storage must be one of {list(STORAGE_MODES)}")

    output_dir = Path(config.output_dir)
    baseline_output_dir = (
        Path(config.baseline_output_dir)
        if config.baseline_output_dir is not None
        else output_dir / "baselines"
    )

    if config.clean:
        _clean_directory(output_dir)
        if config.run_baselines and not _is_relative_to(baseline_output_dir, output_dir):
            _clean_directory(baseline_output_dir)

    synthetic_config = SyntheticDataConfig(
        n_customers=config.n_customers,
        n_rounds=config.n_rounds,
        random_seed=config.random_seed,
        output_dir=output_dir,
        policy_mode=config.policy_mode,
        alpha=config.alpha,
    )
    synthetic_artifacts = run_pipeline(synthetic_config)

    baseline_artifacts = None
    if config.run_baselines:
        baseline_artifacts = run_baseline_comparison(
            n_customers=config.baseline_n_customers,
            train_rounds=config.baseline_train_rounds,
            eval_rounds=config.baseline_eval_rounds,
            random_seed=config.random_seed,
            output_dir=baseline_output_dir,
            ridge_penalty=config.baseline_ridge_penalty,
        )

    manifest = _build_manifest(
        config=config,
        synthetic_config=synthetic_config,
        synthetic_artifacts=synthetic_artifacts,
        baseline_artifacts=baseline_artifacts,
        baseline_output_dir=baseline_output_dir if config.run_baselines else None,
    )
    manifest_path = output_dir / "workflow_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    report_path = output_dir / "workflow_report.md"
    report_path.write_text(_render_workflow_report(manifest) + "\n")

    db_result = None
    if config.storage in {"db", "both"}:
        db_result = persist_csv_artifacts_to_db(
            input_dir=output_dir,
            config=synthetic_config,
            notes=config.db_notes,
        )

    return WorkflowArtifacts(
        output_dir=output_dir,
        baseline_output_dir=baseline_output_dir if config.run_baselines else None,
        manifest_path=manifest_path,
        report_path=report_path,
        db_result=db_result,
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for repeated DS workflow runs."""

    parser = argparse.ArgumentParser(
        description="Run the full repeatable DS workflow without notebooks."
    )
    parser.add_argument("--n-customers", type=int, default=500)
    parser.add_argument("--n-rounds", type=int, default=5000)
    parser.add_argument("--random-seed", type=int, default=42)
    parser.add_argument(
        "--policy-mode",
        choices=sorted(SUPPORTED_POLICY_MODES),
        default="linucb",
    )
    parser.add_argument("--alpha", type=float, default=0.5)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/final_outputs"),
        help="Directory for generated data, final recommendations, EDA, and manifest.",
    )
    parser.add_argument(
        "--keep-existing",
        action="store_true",
        help="Do not clean output directories before running.",
    )
    parser.add_argument(
        "--skip-baselines",
        action="store_true",
        help="Skip the baseline comparison stage.",
    )
    parser.add_argument("--baseline-n-customers", type=int, default=500)
    parser.add_argument("--baseline-train-rounds", type=int, default=5000)
    parser.add_argument("--baseline-eval-rounds", type=int, default=5000)
    parser.add_argument(
        "--baseline-output-dir",
        type=Path,
        default=None,
        help="Directory for baseline artifacts. Defaults to <output-dir>/baselines.",
    )
    parser.add_argument("--baseline-ridge-penalty", type=float, default=5.0)
    parser.add_argument(
        "--storage",
        choices=STORAGE_MODES,
        default="csv",
        help=(
            "Where workflow artifacts are stored. DB mode still writes the local "
            "directory first, then recursively loads it into PostgreSQL."
        ),
    )
    parser.add_argument(
        "--db-notes",
        type=str,
        default=None,
        help="Optional notes stored with the created simulation record in DB mode.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the workflow CLI."""

    parser = build_parser()
    args = parser.parse_args(argv)
    artifacts = run_workflow(
        WorkflowConfig(
            n_customers=args.n_customers,
            n_rounds=args.n_rounds,
            random_seed=args.random_seed,
            policy_mode=args.policy_mode,
            alpha=args.alpha,
            output_dir=args.output_dir,
            clean=not args.keep_existing,
            run_baselines=not args.skip_baselines,
            baseline_n_customers=args.baseline_n_customers,
            baseline_train_rounds=args.baseline_train_rounds,
            baseline_eval_rounds=args.baseline_eval_rounds,
            baseline_output_dir=args.baseline_output_dir,
            baseline_ridge_penalty=args.baseline_ridge_penalty,
            storage=args.storage,
            db_notes=args.db_notes,
        )
    )
    print(artifacts.report_path.read_text())
    print("")
    print(f"Workflow artifacts written to: {artifacts.output_dir}")
    if artifacts.baseline_output_dir is not None:
        print(f"Baseline artifacts written to: {artifacts.baseline_output_dir}")
    if artifacts.db_result is not None:
        print(
            "Persisted to DB: "
            f"simulation_id={artifacts.db_result.simulation_id}, "
            f"customers={artifacts.db_result.customers_inserted}, "
            f"interactions={artifacts.db_result.interactions_inserted}, "
            f"model_state_rows={artifacts.db_result.model_state_rows_upserted}, "
            f"artifacts={artifacts.db_result.artifacts_stored}"
        )
    return 0


def _build_manifest(
    config: WorkflowConfig,
    synthetic_config: SyntheticDataConfig,
    synthetic_artifacts: SyntheticArtifacts,
    baseline_artifacts: BaselineComparisonArtifacts | None,
    baseline_output_dir: Path | None,
) -> dict[str, Any]:
    output_dir = Path(config.output_dir)
    files = sorted(
        {
            *_collect_relative_files(output_dir),
            "workflow_manifest.json",
            "workflow_report.md",
        }
    )
    manifest: dict[str, Any] = {
        "workflow": "campx.ds.run_workflow",
        "reproducible": True,
        "parameters": _manifest_parameters(config),
        "synthetic_run": {
            "simulation_id": synthetic_config.simulation_id,
            "policy_mode": synthetic_config.policy_mode,
            "n_customers": synthetic_config.n_customers,
            "n_rounds": synthetic_config.n_rounds,
            "random_seed": synthetic_config.random_seed,
            "alpha": synthetic_config.alpha,
        },
        "artifact_counts": {
            "customers": len(synthetic_artifacts.customers),
            "interactions": len(synthetic_artifacts.interactions),
            "actions": len(synthetic_artifacts.actions),
            "model_state_rows": len(synthetic_artifacts.model_state),
            "output_files": len(files),
            "eda_pngs": len(list((output_dir / "eda").glob("*.png"))),
        },
        "output_files": files,
        "entrypoints": [
            "python -m campx.ds.run_workflow",
            "python -m campx.ds.generate_synthetic_data",
            "python -m campx.ds.generate_final_outputs",
            "python -m campx.ds.generate_eda_report",
            "python -m campx.ds.run_baseline_comparison",
            "python -m campx.ds.verify_reproducibility",
        ],
    }
    if baseline_artifacts is not None and baseline_output_dir is not None:
        manifest["baseline_run"] = {
            "output_dir": _relative_output_label(baseline_output_dir, output_dir),
            "policies": baseline_artifacts.policy_summary["policy_name"].tolist(),
            "best_policy": str(baseline_artifacts.policy_summary.iloc[0]["policy_name"]),
            "policy_rows": len(baseline_artifacts.policy_summary),
            "round_trace_rows": len(baseline_artifacts.policy_round_traces),
            "output_files": _collect_relative_files(baseline_output_dir),
        }
    return manifest


def _render_workflow_report(manifest: dict[str, Any]) -> str:
    synthetic = manifest["synthetic_run"]
    counts = manifest["artifact_counts"]
    baseline = manifest.get("baseline_run")
    lines = [
        "# Repeatable DS Workflow",
        "",
        f"- Entrypoint: `{manifest['workflow']}`",
        f"- Simulation ID: `{synthetic['simulation_id']}`",
        f"- Policy mode: `{synthetic['policy_mode']}`",
        f"- Random seed: {synthetic['random_seed']}",
        f"- Customers: {counts['customers']}",
        f"- Interactions: {counts['interactions']}",
        f"- EDA PNGs: {counts['eda_pngs']}",
    ]
    if baseline is not None:
        lines.extend(
            [
                f"- Baseline policies: {baseline['policy_rows']}",
                f"- Best baseline policy: `{baseline['best_policy']}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Re-run",
            "",
            "```bash",
            "python -m campx.ds.run_workflow",
            "```",
            "",
            "## Script Entrypoints",
            *[f"- `{entrypoint}`" for entrypoint in manifest["entrypoints"]],
        ]
    )
    return "\n".join(lines)


def _collect_relative_files(directory: Path) -> list[str]:
    if not directory.exists():
        return []
    return sorted(
        str(path.relative_to(directory))
        for path in directory.rglob("*")
        if path.is_file()
    )


def _manifest_parameters(config: WorkflowConfig) -> dict[str, Any]:
    parameters = _json_ready(asdict(config))
    parameters["output_dir"] = "<output-dir>"
    if parameters.get("baseline_output_dir") is not None:
        parameters["baseline_output_dir"] = "<baseline-output-dir>"
    return parameters


def _relative_output_label(path: Path, output_dir: Path) -> str:
    try:
        return str(path.resolve().relative_to(output_dir.resolve()))
    except ValueError:
        return "<baseline-output-dir>"


def _clean_directory(path: Path) -> None:
    resolved = path.resolve()
    unsafe_targets = {
        Path("/").resolve(),
        Path.home().resolve(),
        Path.cwd().resolve(),
    }
    if resolved in unsafe_targets:
        raise ValueError(f"Refusing to clean unsafe output directory: {resolved}")
    if not path.exists():
        return
    shutil.rmtree(path)


def _is_relative_to(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _json_ready(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
