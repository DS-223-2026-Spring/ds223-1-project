"""Verify that DS workflow outputs are reproducible for a fixed seed."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

try:
    from ._routing import load_ds_attr
except ImportError:  # pragma: no cover - supports direct execution in DS container
    from _routing import load_ds_attr

WorkflowConfig = load_ds_attr("run_workflow", "WorkflowConfig")
run_workflow = load_ds_attr("run_workflow", "run_workflow")

DEFAULT_IGNORED_SUFFIXES = {".png"}


@dataclass(frozen=True, slots=True)
class ReproducibilityResult:
    """Summary of one two-run reproducibility verification."""

    run_a_dir: Path
    run_b_dir: Path
    compared_files: tuple[str, ...]
    ignored_files: tuple[str, ...]


def verify_workflow_reproducibility(
    *,
    work_dir: Path,
    n_customers: int,
    n_rounds: int,
    random_seed: int,
    policy_mode: str,
    alpha: float,
    run_baselines: bool,
    baseline_n_customers: int,
    baseline_train_rounds: int,
    baseline_eval_rounds: int,
    baseline_ridge_penalty: float,
    ignored_suffixes: set[str] | None = None,
) -> ReproducibilityResult:
    """Run the workflow twice and compare deterministic artifacts byte-for-byte."""

    ignored_suffixes = ignored_suffixes or set()
    run_a_dir = work_dir / "run_a"
    run_b_dir = work_dir / "run_b"

    _clean_directory(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    common_config = {
        "n_customers": n_customers,
        "n_rounds": n_rounds,
        "random_seed": random_seed,
        "policy_mode": policy_mode,
        "alpha": alpha,
        "clean": True,
        "run_baselines": run_baselines,
        "baseline_n_customers": baseline_n_customers,
        "baseline_train_rounds": baseline_train_rounds,
        "baseline_eval_rounds": baseline_eval_rounds,
        "baseline_ridge_penalty": baseline_ridge_penalty,
        "storage": "csv",
    }

    run_workflow(WorkflowConfig(output_dir=run_a_dir, **common_config))
    run_workflow(WorkflowConfig(output_dir=run_b_dir, **common_config))

    compared_files, ignored_files = _compare_directories(
        run_a_dir,
        run_b_dir,
        ignored_suffixes=ignored_suffixes,
    )
    return ReproducibilityResult(
        run_a_dir=run_a_dir,
        run_b_dir=run_b_dir,
        compared_files=tuple(compared_files),
        ignored_files=tuple(ignored_files),
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for reproducibility verification."""

    parser = argparse.ArgumentParser(
        description="Run the DS workflow twice and verify deterministic outputs."
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=None,
        help="Directory for two temporary runs. Defaults to a new /tmp directory.",
    )
    parser.add_argument("--n-customers", type=int, default=50)
    parser.add_argument("--n-rounds", type=int, default=200)
    parser.add_argument("--random-seed", type=int, default=42)
    parser.add_argument(
        "--policy-mode",
        choices=("bandit_scaffold", "linucb", "random_policy"),
        default="linucb",
    )
    parser.add_argument("--alpha", type=float, default=0.5)
    parser.add_argument(
        "--skip-baselines",
        action="store_true",
        help="Skip baseline comparison while checking synthetic workflow reproducibility.",
    )
    parser.add_argument("--baseline-n-customers", type=int, default=50)
    parser.add_argument("--baseline-train-rounds", type=int, default=200)
    parser.add_argument("--baseline-eval-rounds", type=int, default=200)
    parser.add_argument("--baseline-ridge-penalty", type=float, default=5.0)
    parser.add_argument(
        "--include-png",
        action="store_true",
        help=(
            "Also compare PNG bytes. Off by default because Matplotlib image metadata "
            "can vary across environments."
        ),
    )
    parser.add_argument(
        "--keep-output",
        action="store_true",
        help="Keep temporary run directories after a successful check.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the reproducibility verifier CLI."""

    parser = build_parser()
    args = parser.parse_args(argv)

    created_temp_dir = args.work_dir is None
    work_dir = args.work_dir or Path(tempfile.mkdtemp(prefix="campx_repro_"))
    ignored_suffixes = set() if args.include_png else set(DEFAULT_IGNORED_SUFFIXES)

    try:
        result = verify_workflow_reproducibility(
            work_dir=work_dir,
            n_customers=args.n_customers,
            n_rounds=args.n_rounds,
            random_seed=args.random_seed,
            policy_mode=args.policy_mode,
            alpha=args.alpha,
            run_baselines=not args.skip_baselines,
            baseline_n_customers=args.baseline_n_customers,
            baseline_train_rounds=args.baseline_train_rounds,
            baseline_eval_rounds=args.baseline_eval_rounds,
            baseline_ridge_penalty=args.baseline_ridge_penalty,
            ignored_suffixes=ignored_suffixes,
        )
    except ReproducibilityError as exc:
        print(f"Reproducibility check FAILED: {exc}")
        print(f"Work directory: {work_dir}")
        return 1

    print("Reproducibility check OK")
    print(f"Compared files: {len(result.compared_files)}")
    print(f"Ignored files: {len(result.ignored_files)}")
    print(f"Run A: {result.run_a_dir}")
    print(f"Run B: {result.run_b_dir}")

    if created_temp_dir and not args.keep_output:
        shutil.rmtree(work_dir)
        print("Temporary output removed; pass --keep-output to inspect run directories.")
    return 0


class ReproducibilityError(RuntimeError):
    """Raised when two workflow runs differ."""


def _compare_directories(
    left: Path,
    right: Path,
    *,
    ignored_suffixes: set[str],
) -> tuple[list[str], list[str]]:
    left_files = _relative_files(left)
    right_files = _relative_files(right)

    ignored_files = sorted(
        path
        for path in left_files | right_files
        if Path(path).suffix.lower() in ignored_suffixes
    )
    comparable_left = {
        path
        for path in left_files
        if Path(path).suffix.lower() not in ignored_suffixes
    }
    comparable_right = {
        path
        for path in right_files
        if Path(path).suffix.lower() not in ignored_suffixes
    }

    if comparable_left != comparable_right:
        missing_from_right = sorted(comparable_left - comparable_right)
        missing_from_left = sorted(comparable_right - comparable_left)
        raise ReproducibilityError(
            "file sets differ; "
            f"missing from run_b={missing_from_right}, "
            f"missing from run_a={missing_from_left}"
        )

    mismatches = []
    for relative_path in sorted(comparable_left):
        left_hash = _sha256(left / relative_path)
        right_hash = _sha256(right / relative_path)
        if left_hash != right_hash:
            mismatches.append(
                f"{relative_path} ({left_hash[:12]} != {right_hash[:12]})"
            )

    if mismatches:
        raise ReproducibilityError(
            "artifact content differs: " + "; ".join(mismatches[:10])
        )

    return sorted(comparable_left), ignored_files


def _relative_files(directory: Path) -> set[str]:
    return {
        path.relative_to(directory).as_posix()
        for path in directory.rglob("*")
        if path.is_file()
    }


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _clean_directory(path: Path) -> None:
    resolved = path.resolve()
    unsafe_targets = {
        Path("/").resolve(),
        Path.home().resolve(),
        Path.cwd().resolve(),
    }
    if resolved in unsafe_targets:
        raise ValueError(f"Refusing to clean unsafe reproducibility directory: {resolved}")
    if path.exists():
        shutil.rmtree(path)


if __name__ == "__main__":
    raise SystemExit(main())
