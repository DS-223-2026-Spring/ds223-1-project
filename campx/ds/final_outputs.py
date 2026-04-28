"""Customer-level final output generation from learned DS model state."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    from ._routing import import_ds_module, load_ds_attr
except ImportError:  # pragma: no cover - supports direct execution in DS container
    from _routing import import_ds_module, load_ds_attr

_config = import_ds_module("synthetic.config")
FEATURE_COLUMNS = _config.FEATURE_COLUMNS
build_context_matrix = load_ds_attr("synthetic.features", "build_context_matrix")


@dataclass(slots=True)
class FinalOutputArtifacts:
    """Exported customer recommendations and supporting score tables."""

    output_dir: Path
    customer_recommendations: pd.DataFrame
    customer_action_scores: pd.DataFrame
    recommendation_summary: pd.DataFrame
    report_path: Path
    eda_output_dir: Path | None = None
    eda_report_path: Path | None = None


def build_final_outputs(
    customers: pd.DataFrame,
    actions: pd.DataFrame,
    model_state: pd.DataFrame,
    output_dir: Path | str,
    include_eda: bool = True,
    eda_input_dir: Path | str | None = None,
    eda_output_dir: Path | str | None = None,
    max_scatter_points: int = 2000,
    eda_random_seed: int = 42,
) -> FinalOutputArtifacts:
    """Build recommendations and optional EDA outputs from final model state."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    customer_action_scores = score_customer_actions(
        customers=customers,
        actions=actions,
        model_state=model_state,
    )
    customer_recommendations = build_customer_recommendations(
        customers=customers,
        customer_action_scores=customer_action_scores,
    )
    recommendation_summary = summarize_recommendations(customer_recommendations)

    customer_recommendations.to_csv(
        output_path / "customer_recommendations.csv",
        index=False,
    )
    customer_action_scores.to_csv(
        output_path / "customer_action_scores.csv",
        index=False,
    )
    recommendation_summary.to_csv(
        output_path / "recommendation_summary.csv",
        index=False,
    )

    report_path = output_path / "final_output_report.md"
    report_path.write_text(
        _render_report(
            customer_recommendations=customer_recommendations,
            recommendation_summary=recommendation_summary,
            model_state=model_state,
            include_eda=include_eda,
        )
        + "\n"
    )

    eda_artifacts = None
    if include_eda:
        eda_artifacts = _run_eda(
            input_dir=Path(eda_input_dir) if eda_input_dir is not None else output_path,
            output_dir=Path(eda_output_dir) if eda_output_dir is not None else output_path / "eda",
            max_scatter_points=max_scatter_points,
            random_seed=eda_random_seed,
        )

    return FinalOutputArtifacts(
        output_dir=output_path,
        customer_recommendations=customer_recommendations,
        customer_action_scores=customer_action_scores,
        recommendation_summary=recommendation_summary,
        report_path=report_path,
        eda_output_dir=eda_artifacts.output_dir if eda_artifacts is not None else None,
        eda_report_path=eda_artifacts.report_path if eda_artifacts is not None else None,
    )


def score_customer_actions(
    customers: pd.DataFrame,
    actions: pd.DataFrame,
    model_state: pd.DataFrame,
) -> pd.DataFrame:
    """Score every available action for every customer."""

    if model_state.empty:
        raise ValueError("model_state must contain one row per action")

    state = _prepare_model_state(model_state=model_state, actions=actions)
    feature_columns, feature_means, feature_scales = _extract_feature_transform(
        customers=customers,
        model_state=state,
    )
    contexts = (
        build_context_matrix(customers=customers, feature_columns=feature_columns)
        - feature_means
    ) / feature_scales

    score_frames: list[pd.DataFrame] = []
    customer_index = customers[["customer_id", "segment"]].reset_index(drop=True)
    for row in state.sort_values("action_id").itertuples(index=False):
        action_id = int(row.action_id)
        theta = np.array(_json_array(row.theta_json), dtype=float)
        a_matrix = np.array(_json_array(row.a_json), dtype=float)
        alpha = float(row.alpha)

        if theta.shape[0] != contexts.shape[1]:
            raise ValueError(
                f"theta length for action_id={action_id} does not match context dimension"
            )
        if a_matrix.shape != (contexts.shape[1], contexts.shape[1]):
            raise ValueError(
                f"A matrix shape for action_id={action_id} does not match context dimension"
            )

        predicted_reward = contexts @ theta
        solved_contexts = np.linalg.solve(a_matrix, contexts.T).T
        uncertainty = np.sum(contexts * solved_contexts, axis=1)
        uncertainty = np.clip(uncertainty, 0.0, None)
        explore_score = alpha * np.sqrt(uncertainty)
        ucb_score = predicted_reward + explore_score

        frame = customer_index.copy()
        frame["action_id"] = action_id
        frame["action_name"] = str(row.action_name)
        frame["base_cost"] = float(row.base_cost)
        frame["predicted_reward"] = np.round(predicted_reward, 4)
        frame["uncertainty_score"] = np.round(uncertainty, 4)
        frame["explore_score"] = np.round(explore_score, 4)
        frame["ucb_score"] = np.round(ucb_score, 4)
        frame["n_pulls"] = int(row.n_pulls)
        score_frames.append(frame)

    scores = pd.concat(score_frames, ignore_index=True)
    scores = scores.sort_values(
        ["customer_id", "ucb_score", "predicted_reward", "action_id"],
        ascending=[True, False, False, True],
        kind="mergesort",
    ).reset_index(drop=True)
    scores["action_rank"] = scores.groupby("customer_id").cumcount() + 1
    scores["confidence_score"] = (
        scores.groupby("customer_id")["ucb_score"]
        .transform(_softmax_series)
        .round(4)
    )
    return scores[
        [
            "customer_id",
            "segment",
            "action_rank",
            "action_id",
            "action_name",
            "base_cost",
            "predicted_reward",
            "uncertainty_score",
            "explore_score",
            "ucb_score",
            "confidence_score",
            "n_pulls",
        ]
    ]


def build_customer_recommendations(
    customers: pd.DataFrame,
    customer_action_scores: pd.DataFrame,
) -> pd.DataFrame:
    """Return one final recommendation row per customer."""

    winners = (
        customer_action_scores.loc[customer_action_scores["action_rank"] == 1]
        .drop(columns=["action_rank"])
        .rename(
            columns={
                "action_id": "recommended_action_id",
                "action_name": "recommended_action_name",
                "base_cost": "recommended_action_cost",
                "ucb_score": "recommended_ucb_score",
                "n_pulls": "recommended_action_n_pulls",
            }
        )
    )
    runners_up = (
        customer_action_scores.loc[customer_action_scores["action_rank"] == 2]
        .loc[:, ["customer_id", "action_id", "action_name", "ucb_score"]]
        .rename(
            columns={
                "action_id": "runner_up_action_id",
                "action_name": "runner_up_action_name",
                "ucb_score": "runner_up_ucb_score",
            }
        )
    )
    winners = winners.merge(runners_up, on="customer_id", how="left")
    winners["score_margin"] = (
        winners["recommended_ucb_score"] - winners["runner_up_ucb_score"]
    ).round(4)

    customer_columns = [
        column
        for column in [
            "customer_id",
            "gender",
            "segment",
            *FEATURE_COLUMNS,
        ]
        if column in customers.columns
    ]
    recommendations = customers.loc[:, customer_columns].merge(
        winners.drop(columns=["segment"]),
        on="customer_id",
        how="left",
    )
    return recommendations[
        [
            *customer_columns,
            "recommended_action_id",
            "recommended_action_name",
            "recommended_action_cost",
            "predicted_reward",
            "confidence_score",
            "uncertainty_score",
            "explore_score",
            "recommended_ucb_score",
            "runner_up_action_id",
            "runner_up_action_name",
            "runner_up_ucb_score",
            "score_margin",
            "recommended_action_n_pulls",
        ]
    ]


def summarize_recommendations(customer_recommendations: pd.DataFrame) -> pd.DataFrame:
    """Aggregate final recommendation mix by segment and action."""

    summary = (
        customer_recommendations.groupby(
            ["segment", "recommended_action_id", "recommended_action_name"],
            as_index=False,
        )
        .agg(
            customers=("customer_id", "count"),
            mean_predicted_reward=("predicted_reward", "mean"),
            mean_confidence_score=("confidence_score", "mean"),
            mean_uncertainty_score=("uncertainty_score", "mean"),
            mean_score_margin=("score_margin", "mean"),
        )
        .sort_values(["segment", "customers"], ascending=[True, False])
        .reset_index(drop=True)
    )
    segment_totals = summary.groupby("segment")["customers"].transform("sum")
    summary["segment_share"] = summary["customers"] / segment_totals
    summary["overall_share"] = summary["customers"] / len(customer_recommendations)
    summary["rank_within_segment"] = summary.groupby("segment").cumcount() + 1
    return summary[
        [
            "segment",
            "rank_within_segment",
            "recommended_action_id",
            "recommended_action_name",
            "customers",
            "segment_share",
            "overall_share",
            "mean_predicted_reward",
            "mean_confidence_score",
            "mean_uncertainty_score",
            "mean_score_margin",
        ]
    ].round(
        {
            "segment_share": 4,
            "overall_share": 4,
            "mean_predicted_reward": 4,
            "mean_confidence_score": 4,
            "mean_uncertainty_score": 4,
            "mean_score_margin": 4,
        }
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for final output generation."""

    parser = argparse.ArgumentParser(
        description="Build customer-level final recommendation outputs from DS artifacts."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("outputs/synthetic_data"),
        help="Directory containing customers.csv, actions.csv, and model_state.csv.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for final output files. Defaults to --input-dir.",
    )
    parser.add_argument(
        "--skip-eda",
        action="store_true",
        help="Only write recommendation outputs; by default EDA tables and plots are also written.",
    )
    parser.add_argument(
        "--eda-output-dir",
        type=Path,
        default=None,
        help="Directory for EDA tables and plots. Defaults to <output-dir>/eda.",
    )
    parser.add_argument(
        "--max-scatter-points",
        type=int,
        default=2000,
        help="Maximum number of customer points rendered in EDA scatter plots.",
    )
    parser.add_argument(
        "--eda-random-seed",
        type=int,
        default=42,
        help="Seed used for reproducible EDA plot subsampling.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the final output generation CLI."""

    parser = build_parser()
    args = parser.parse_args(argv)
    output_dir = args.output_dir or args.input_dir
    artifacts = build_final_outputs_from_dir(
        input_dir=args.input_dir,
        output_dir=output_dir,
        include_eda=not args.skip_eda,
        eda_output_dir=args.eda_output_dir,
        max_scatter_points=args.max_scatter_points,
        eda_random_seed=args.eda_random_seed,
    )
    print(artifacts.report_path.read_text())
    print("")
    print(f"Final output artifacts written to: {artifacts.output_dir}")
    return 0


def build_final_outputs_from_dir(
    input_dir: Path | str,
    output_dir: Path | str,
    include_eda: bool = True,
    eda_output_dir: Path | str | None = None,
    max_scatter_points: int = 2000,
    eda_random_seed: int = 42,
) -> FinalOutputArtifacts:
    """Load synthetic artifacts from disk and write final recommendation outputs."""

    input_path = Path(input_dir)
    customers = pd.read_csv(input_path / "customers.csv")
    actions = pd.read_csv(input_path / "actions.csv")
    model_state = pd.read_csv(input_path / "model_state.csv")
    return build_final_outputs(
        customers=customers,
        actions=actions,
        model_state=model_state,
        output_dir=output_dir,
        include_eda=include_eda,
        eda_input_dir=input_path,
        eda_output_dir=eda_output_dir,
        max_scatter_points=max_scatter_points,
        eda_random_seed=eda_random_seed,
    )


def _prepare_model_state(
    model_state: pd.DataFrame,
    actions: pd.DataFrame,
) -> pd.DataFrame:
    state = model_state.copy()
    action_metadata_columns = [
        column
        for column in ["action_id", "action_name", "base_cost"]
        if column in actions.columns
    ]
    action_metadata = actions.loc[:, action_metadata_columns].copy()
    if "action_name" in state.columns:
        state = state.drop(columns=["action_name"])
    state = state.merge(action_metadata, on="action_id", how="left")
    if "action_name" not in state.columns:
        state["action_name"] = pd.NA
    if "base_cost" not in state.columns:
        state["base_cost"] = 0.0
    state["action_name"] = state["action_name"].fillna(
        state["action_id"].map(lambda action_id: f"action_{action_id}")
    )
    state["base_cost"] = state["base_cost"].fillna(0.0)
    return state


def _extract_feature_transform(
    customers: pd.DataFrame,
    model_state: pd.DataFrame,
) -> tuple[list[str], np.ndarray, np.ndarray]:
    first_row = model_state.iloc[0]
    feature_columns = _json_array(
        first_row.get("feature_columns_json"),
        fallback=FEATURE_COLUMNS,
    )
    feature_columns = [str(column) for column in feature_columns]
    feature_matrix = build_context_matrix(customers=customers, feature_columns=feature_columns)
    default_means = [0.0] * len(feature_columns)
    default_scales = np.max(np.abs(feature_matrix), axis=0).tolist()

    feature_means = np.array(
        _json_array(first_row.get("feature_means_json"), fallback=default_means),
        dtype=float,
    )
    feature_scales = np.array(
        _json_array(first_row.get("feature_scales_json"), fallback=default_scales),
        dtype=float,
    )
    feature_scales = np.where(np.abs(feature_scales) < 1e-8, 1.0, feature_scales)
    return feature_columns, feature_means, feature_scales


def _json_array(value: Any, fallback: Any | None = None) -> Any:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        if fallback is None:
            raise ValueError("Missing required JSON array value")
        return fallback
    if isinstance(value, str):
        return json.loads(value)
    return value


def _softmax_series(values: pd.Series) -> np.ndarray:
    raw = values.to_numpy(dtype=float)
    if len(raw) == 0:
        return raw
    centered = raw - np.max(raw)
    weights = np.exp(np.clip(centered, -700.0, 0.0))
    denominator = weights.sum()
    if denominator <= 0:
        return np.full(len(raw), 1.0 / len(raw))
    return weights / denominator


def _render_report(
    customer_recommendations: pd.DataFrame,
    recommendation_summary: pd.DataFrame,
    model_state: pd.DataFrame,
    include_eda: bool,
) -> str:
    simulation_id = _unique_label(model_state, "simulation_id")
    policy_mode = _unique_label(model_state, "policy_mode")
    top_action = (
        customer_recommendations["recommended_action_name"]
        .value_counts()
        .rename_axis("action")
        .reset_index(name="customers")
        .iloc[0]
    )
    segment_lines = [
        (
            f"- {row.segment}: `{row.recommended_action_name}` "
            f"for {int(row.customers)} customers "
            f"({row.segment_share:.1%} of segment)"
        )
        for row in recommendation_summary.loc[
            recommendation_summary["rank_within_segment"] == 1
        ].itertuples(index=False)
    ]
    mean_confidence = customer_recommendations["confidence_score"].mean()
    mean_margin = customer_recommendations["score_margin"].mean()

    return "\n".join(
        [
            "# Final DS Outputs",
            "",
            f"- Simulation ID: `{simulation_id}`",
            f"- Policy mode: `{policy_mode}`",
            f"- Customers scored: {len(customer_recommendations)}",
            (
                f"- Most common recommendation: `{top_action.action}` "
                f"for {int(top_action.customers)} customers"
            ),
            f"- Mean confidence score: {mean_confidence:.4f}",
            f"- Mean top-vs-runner-up UCB margin: {mean_margin:.4f}",
            "",
            "## Top Recommendation by Segment",
            *segment_lines,
            "",
            "## Files",
            "- `customer_recommendations.csv`: one final action per customer with segment, features, confidence, and UCB margin.",
            "- `customer_action_scores.csv`: every customer-action score used to choose the recommendation.",
            "- `recommendation_summary.csv`: segment-level recommendation mix and confidence summary.",
            (
                "- `eda/`: automatically generated EDA tables and plots for the same dataset."
                if include_eda
                else "- EDA export skipped for this run."
            ),
        ]
    )


def _run_eda(
    input_dir: Path,
    output_dir: Path,
    max_scatter_points: int,
    random_seed: int,
):
    run_eda = load_ds_attr("eda", "run_eda")

    return run_eda(
        input_dir=input_dir,
        output_dir=output_dir,
        max_scatter_points=max_scatter_points,
        random_seed=random_seed,
    )


def _unique_label(frame: pd.DataFrame, column: str) -> str:
    if column not in frame.columns:
        return "unknown"
    values = frame[column].dropna().astype(str).unique()
    if len(values) == 0:
        return "unknown"
    if len(values) == 1:
        return values[0]
    return "multiple"


if __name__ == "__main__":
    raise SystemExit(main())
