"""Baseline policy benchmarking for the synthetic retail personalization task."""

from __future__ import annotations

import argparse
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "ds223_matplotlib"))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    from .synthetic.actions import actions_to_frame, get_action_definitions
    from .synthetic.config import FEATURE_COLUMNS, GeneratorCalibration, SyntheticDataConfig
    from .synthetic.features import generate_observed_features
    from .synthetic.latents import generate_latent_traits
    from .synthetic.simulate import (
        compute_conversion_probabilities,
        compute_realized_costs,
        sample_customer_rounds,
        simulate_interactions,
        simulate_revenue,
    )
except ImportError:  # pragma: no cover - supports running inside the ds container
    from synthetic.actions import actions_to_frame, get_action_definitions
    from synthetic.config import FEATURE_COLUMNS, GeneratorCalibration, SyntheticDataConfig
    from synthetic.features import generate_observed_features
    from synthetic.latents import generate_latent_traits
    from synthetic.simulate import (
        compute_conversion_probabilities,
        compute_realized_costs,
        sample_customer_rounds,
        simulate_interactions,
        simulate_revenue,
    )

HEURISTIC_SEGMENT_ACTIONS = {
    "Champion": 0,
    "Loyal": 3,
    "At-Risk": 2,
    "Lost": 1,
}


@dataclass(slots=True)
class BaselineComparisonArtifacts:
    """Structured outputs from one baseline comparison run."""

    output_dir: Path
    policy_summary: pd.DataFrame
    policy_action_distribution: pd.DataFrame
    policy_round_traces: pd.DataFrame
    training_action_summary: pd.DataFrame
    policy_mapping: pd.DataFrame
    linear_model_coefficients: pd.DataFrame
    report_path: Path


@dataclass(slots=True)
class ConstantActionPolicy:
    """Always choose one fixed action."""

    name: str
    action_id: int

    def choose_actions(
        self,
        sampled_customers: pd.DataFrame,
        rng: np.random.Generator,
    ) -> np.ndarray:
        del rng
        return np.full(len(sampled_customers), self.action_id, dtype=int)


@dataclass(slots=True)
class RandomPolicy:
    """Uniform random baseline."""

    name: str
    action_ids: np.ndarray

    def choose_actions(
        self,
        sampled_customers: pd.DataFrame,
        rng: np.random.Generator,
    ) -> np.ndarray:
        return rng.choice(self.action_ids, size=len(sampled_customers), replace=True)


@dataclass(slots=True)
class SegmentMappingPolicy:
    """Choose actions from a segment-to-action lookup."""

    name: str
    segment_to_action_id: dict[str, int]
    fallback_action_id: int

    def choose_actions(
        self,
        sampled_customers: pd.DataFrame,
        rng: np.random.Generator,
    ) -> np.ndarray:
        del rng
        return (
            sampled_customers["segment"]
            .map(self.segment_to_action_id)
            .fillna(self.fallback_action_id)
            .astype(int)
            .to_numpy()
        )


@dataclass(slots=True)
class LinearRewardPolicy:
    """Per-action ridge regressions over observed customer features."""

    name: str
    action_ids: np.ndarray
    feature_means: np.ndarray
    feature_scales: np.ndarray
    coefficients: np.ndarray

    def choose_actions(
        self,
        sampled_customers: pd.DataFrame,
        rng: np.random.Generator,
    ) -> np.ndarray:
        del rng
        features = sampled_customers[FEATURE_COLUMNS].to_numpy(dtype=float)
        standardized = (features - self.feature_means) / self.feature_scales
        design = np.column_stack([np.ones(len(standardized)), standardized])
        predictions = design @ self.coefficients.T
        best_indices = np.argmax(predictions, axis=1)
        return self.action_ids[best_indices]


def run_baseline_comparison(
    n_customers: int = 500,
    train_rounds: int = 5000,
    eval_rounds: int = 5000,
    random_seed: int = 42,
    output_dir: Path | str = Path("outputs/baselines"),
    ridge_penalty: float = 5.0,
    calibration: GeneratorCalibration | None = None,
) -> BaselineComparisonArtifacts:
    """Train simple baselines on logged random data and compare them on holdout data."""

    calibration = calibration or GeneratorCalibration()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    actions = get_action_definitions(calibration)
    actions_frame = actions_to_frame(actions)
    action_ids = actions_frame["action_id"].to_numpy(dtype=int)
    action_lookup = dict(zip(actions_frame["action_id"], actions_frame["action_name"], strict=True))

    train_customers, train_latents = _generate_customer_population(
        n_customers=n_customers,
        random_seed=random_seed,
        calibration=calibration,
    )
    train_config = SyntheticDataConfig(
        n_customers=n_customers,
        n_rounds=train_rounds,
        random_seed=random_seed,
        output_dir=output_dir,
        simulation_id=f"baseline_train_seed{random_seed}",
        policy_mode="random_policy",
        calibration=calibration,
    )
    training_rng = np.random.default_rng(random_seed + 101)
    training_interactions, _ = simulate_interactions(
        customers=train_customers,
        latents=train_latents,
        actions=actions,
        config=train_config,
        rng=training_rng,
    )
    training_logged = training_interactions.merge(
        train_customers,
        on="customer_id",
        how="left",
    )

    training_action_summary = _build_training_action_summary(training_logged, actions_frame)
    global_best_action_id = _select_global_best_action(training_logged, actions_frame)

    heuristic_policy = SegmentMappingPolicy(
        name="segment_heuristic",
        segment_to_action_id=HEURISTIC_SEGMENT_ACTIONS,
        fallback_action_id=global_best_action_id,
    )
    segment_lookup_policy = SegmentMappingPolicy(
        name="segment_reward_lookup",
        segment_to_action_id=_fit_segment_reward_mapping(
            training_logged=training_logged,
            actions_frame=actions_frame,
            fallback_action_id=global_best_action_id,
        ),
        fallback_action_id=global_best_action_id,
    )
    linear_reward_policy = _fit_linear_reward_policy(
        training_logged=training_logged,
        actions_frame=actions_frame,
        ridge_penalty=ridge_penalty,
    )

    policies = [
        RandomPolicy(name="random_uniform", action_ids=action_ids),
        ConstantActionPolicy(name="best_historical_action", action_id=global_best_action_id),
        heuristic_policy,
        segment_lookup_policy,
        linear_reward_policy,
    ]

    test_customers, test_latents = _generate_customer_population(
        n_customers=n_customers,
        random_seed=random_seed + 1,
        calibration=calibration,
    )
    test_customer_frame = test_customers.merge(test_latents, on="customer_id", how="inner")
    eval_config = SyntheticDataConfig(
        n_customers=n_customers,
        n_rounds=eval_rounds,
        random_seed=random_seed + 1,
        output_dir=output_dir,
        simulation_id=f"baseline_eval_seed{random_seed}",
        policy_mode="bandit_scaffold",
        calibration=calibration,
    )
    sampled_customers = sample_customer_rounds(
        customer_frame=test_customer_frame,
        n_rounds=eval_rounds,
        config=eval_config,
        rng=np.random.default_rng(random_seed + 202),
    )

    policy_interactions = []
    for index, policy in enumerate(policies):
        action_rng = np.random.default_rng(random_seed + 303 + index)
        selected_action_ids = policy.choose_actions(sampled_customers, action_rng)
        evaluation_rng = np.random.default_rng(random_seed + 404 + index)
        interactions = _evaluate_action_sequence(
            sampled_customers=sampled_customers,
            action_ids=selected_action_ids,
            actions=actions,
            actions_frame=actions_frame,
            config=eval_config,
            rng=evaluation_rng,
            policy_name=policy.name,
        )
        policy_interactions.append(interactions)

    policy_round_traces = pd.concat(policy_interactions, ignore_index=True)
    policy_summary = _build_policy_summary(policy_round_traces).sort_values(
        "total_reward",
        ascending=False,
    ).reset_index(drop=True)
    policy_action_distribution = _build_policy_action_distribution(
        policy_round_traces=policy_round_traces,
        actions_frame=actions_frame,
    )
    policy_mapping = _build_policy_mapping_frame(
        actions_frame=actions_frame,
        global_best_action_id=global_best_action_id,
        heuristic_policy=heuristic_policy,
        segment_lookup_policy=segment_lookup_policy,
    )
    linear_model_coefficients = _build_linear_coefficients_frame(
        policy=linear_reward_policy,
        actions_frame=actions_frame,
    )

    policy_summary.to_csv(output_dir / "policy_summary.csv", index=False)
    policy_action_distribution.to_csv(output_dir / "policy_action_distribution.csv", index=False)
    policy_round_traces.to_csv(output_dir / "policy_round_traces.csv", index=False)
    training_action_summary.to_csv(output_dir / "training_action_summary.csv", index=False)
    policy_mapping.to_csv(output_dir / "policy_mapping.csv", index=False)
    linear_model_coefficients.to_csv(output_dir / "linear_model_coefficients.csv", index=False)

    _plot_cumulative_reward(policy_round_traces, output_dir / "cumulative_reward_by_policy.png")
    _plot_policy_total_reward(policy_summary, output_dir / "total_reward_by_policy.png")
    _plot_policy_action_mix(
        policy_action_distribution,
        output_dir / "action_mix_by_policy.png",
        actions_frame,
    )

    report_path = output_dir / "baseline_report.md"
    report_path.write_text(
        _render_report(
            policy_summary=policy_summary,
            training_action_summary=training_action_summary,
            policy_mapping=policy_mapping,
            n_customers=n_customers,
            train_rounds=train_rounds,
            eval_rounds=eval_rounds,
            random_seed=random_seed,
        )
        + "\n"
    )

    return BaselineComparisonArtifacts(
        output_dir=output_dir,
        policy_summary=policy_summary,
        policy_action_distribution=policy_action_distribution,
        policy_round_traces=policy_round_traces,
        training_action_summary=training_action_summary,
        policy_mapping=policy_mapping,
        linear_model_coefficients=linear_model_coefficients,
        report_path=report_path,
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for baseline comparison runs."""

    parser = argparse.ArgumentParser(
        description="Train and compare simple baseline policies for synthetic retail personalization."
    )
    parser.add_argument("--n-customers", type=int, default=500)
    parser.add_argument("--train-rounds", type=int, default=5000)
    parser.add_argument("--eval-rounds", type=int, default=5000)
    parser.add_argument("--random-seed", type=int, default=42)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/baselines"),
    )
    parser.add_argument(
        "--ridge-penalty",
        type=float,
        default=5.0,
        help="L2 penalty used by the per-action linear reward model.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the baseline benchmark CLI."""

    parser = build_parser()
    args = parser.parse_args(argv)
    artifacts = run_baseline_comparison(
        n_customers=args.n_customers,
        train_rounds=args.train_rounds,
        eval_rounds=args.eval_rounds,
        random_seed=args.random_seed,
        output_dir=args.output_dir,
        ridge_penalty=args.ridge_penalty,
    )

    print(artifacts.report_path.read_text())
    print("")
    print(f"Artifacts written to: {artifacts.output_dir}")
    return 0


def _generate_customer_population(
    n_customers: int,
    random_seed: int,
    calibration: GeneratorCalibration,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(random_seed)
    latents = generate_latent_traits(n_customers, calibration, rng)
    customers = generate_observed_features(latents, calibration, rng)
    return customers, latents


def _build_training_action_summary(
    training_logged: pd.DataFrame,
    actions_frame: pd.DataFrame,
) -> pd.DataFrame:
    summary = (
        training_logged.groupby("action_id", as_index=False)
        .agg(
            observations=("interaction_id", "count"),
            mean_reward=("reward", "mean"),
            mean_conversion_rate=("converted", "mean"),
            mean_revenue=("revenue", "mean"),
            mean_cost=("cost", "mean"),
        )
        .merge(actions_frame[["action_id", "action_name"]], on="action_id", how="left")
        .round(
            {
                "mean_reward": 2,
                "mean_conversion_rate": 4,
                "mean_revenue": 2,
                "mean_cost": 2,
            }
        )
        .sort_values("action_id")
        .reset_index(drop=True)
    )
    return summary[
        [
            "action_id",
            "action_name",
            "observations",
            "mean_reward",
            "mean_conversion_rate",
            "mean_revenue",
            "mean_cost",
        ]
    ]


def _select_global_best_action(
    training_logged: pd.DataFrame,
    actions_frame: pd.DataFrame,
) -> int:
    mean_rewards = (
        training_logged.groupby("action_id")["reward"].mean().reindex(actions_frame["action_id"])
    )
    return int(mean_rewards.idxmax())


def _fit_segment_reward_mapping(
    training_logged: pd.DataFrame,
    actions_frame: pd.DataFrame,
    fallback_action_id: int,
) -> dict[str, int]:
    grid = pd.MultiIndex.from_product(
        [
            ["Champion", "Loyal", "At-Risk", "Lost"],
            actions_frame["action_id"].tolist(),
        ],
        names=["segment", "action_id"],
    )
    mean_rewards = (
        training_logged.groupby(["segment", "action_id"])["reward"]
        .mean()
        .reindex(grid)
        .reset_index()
    )
    segment_mapping: dict[str, int] = {}
    for segment, segment_frame in mean_rewards.groupby("segment"):
        filled = segment_frame.copy()
        filled["reward"] = filled["reward"].fillna(-np.inf)
        if np.isneginf(filled["reward"]).all():
            segment_mapping[segment] = fallback_action_id
            continue
        best_row = filled.sort_values("reward", ascending=False).iloc[0]
        segment_mapping[segment] = int(best_row["action_id"])
    return segment_mapping


def _fit_linear_reward_policy(
    training_logged: pd.DataFrame,
    actions_frame: pd.DataFrame,
    ridge_penalty: float,
) -> LinearRewardPolicy:
    features = training_logged[FEATURE_COLUMNS].to_numpy(dtype=float)
    feature_means = features.mean(axis=0)
    feature_scales = features.std(axis=0)
    feature_scales = np.where(feature_scales < 1e-8, 1.0, feature_scales)

    coefficients = []
    for action_id in actions_frame["action_id"]:
        subset = training_logged.loc[training_logged["action_id"] == action_id]
        action_mean = float(subset["reward"].mean()) if not subset.empty else 0.0
        if subset.empty:
            beta = np.zeros(len(FEATURE_COLUMNS) + 1, dtype=float)
            beta[0] = action_mean
            coefficients.append(beta)
            continue

        x = subset[FEATURE_COLUMNS].to_numpy(dtype=float)
        y = subset["reward"].to_numpy(dtype=float)
        standardized = (x - feature_means) / feature_scales
        design = np.column_stack([np.ones(len(standardized)), standardized])
        penalty = np.eye(design.shape[1], dtype=float) * ridge_penalty
        penalty[0, 0] = 0.0
        beta = np.linalg.solve(design.T @ design + penalty, design.T @ y)
        coefficients.append(beta)

    return LinearRewardPolicy(
        name="linear_reward_model",
        action_ids=actions_frame["action_id"].to_numpy(dtype=int),
        feature_means=feature_means,
        feature_scales=feature_scales,
        coefficients=np.vstack(coefficients),
    )


def _evaluate_action_sequence(
    sampled_customers: pd.DataFrame,
    action_ids: np.ndarray,
    actions,
    actions_frame: pd.DataFrame,
    config: SyntheticDataConfig,
    rng: np.random.Generator,
    policy_name: str,
) -> pd.DataFrame:
    round_numbers = np.arange(1, len(sampled_customers) + 1, dtype=int)
    p_convert = compute_conversion_probabilities(
        action_ids=action_ids,
        sampled_customers=sampled_customers,
        actions=actions,
        config=config,
    )
    converted = rng.random(len(sampled_customers)) < p_convert
    revenue = simulate_revenue(
        sampled_customers=sampled_customers,
        action_ids=action_ids,
        actions=actions,
        round_numbers=round_numbers,
        converted=converted,
        config=config,
        rng=rng,
    )
    cost = compute_realized_costs(
        action_ids=action_ids,
        revenue=revenue,
        converted=converted,
        actions=actions,
    )
    reward = revenue - cost

    interactions = pd.DataFrame(
        {
            "policy_name": policy_name,
            "round_number": round_numbers,
            "customer_id": sampled_customers["customer_id"].astype(int).to_numpy(),
            "segment": sampled_customers["segment"].astype(str).to_numpy(),
            "action_id": action_ids.astype(int),
            "converted": converted.astype(bool),
            "revenue": np.round(revenue, 2),
            "cost": np.round(cost, 2),
            "reward": np.round(reward, 2),
            "p_convert": np.round(p_convert, 4),
            "simulation_id": f"{config.simulation_id}_{policy_name}",
        }
    ).merge(actions_frame[["action_id", "action_name"]], on="action_id", how="left")
    interactions["cumulative_reward"] = interactions["reward"].cumsum().round(2)
    return interactions


def _build_policy_summary(policy_round_traces: pd.DataFrame) -> pd.DataFrame:
    return (
        policy_round_traces.groupby("policy_name", as_index=False)
        .agg(
            total_reward=("reward", "sum"),
            mean_reward=("reward", "mean"),
            conversion_rate=("converted", "mean"),
            mean_revenue=("revenue", "mean"),
            mean_cost=("cost", "mean"),
            mean_p_convert=("p_convert", "mean"),
            final_cumulative_reward=("cumulative_reward", "max"),
        )
        .round(
            {
                "total_reward": 2,
                "mean_reward": 2,
                "conversion_rate": 4,
                "mean_revenue": 2,
                "mean_cost": 2,
                "mean_p_convert": 4,
                "final_cumulative_reward": 2,
            }
        )
    )


def _build_policy_action_distribution(
    policy_round_traces: pd.DataFrame,
    actions_frame: pd.DataFrame,
) -> pd.DataFrame:
    counts = (
        policy_round_traces.groupby(["policy_name", "action_id"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
    )
    totals = counts.groupby("policy_name")["count"].transform("sum")
    counts["share"] = (counts["count"] / totals).round(4)
    return (
        counts.merge(actions_frame[["action_id", "action_name"]], on="action_id", how="left")
        .sort_values(["policy_name", "action_id"])
        .reset_index(drop=True)
    )


def _build_policy_mapping_frame(
    actions_frame: pd.DataFrame,
    global_best_action_id: int,
    heuristic_policy: SegmentMappingPolicy,
    segment_lookup_policy: SegmentMappingPolicy,
) -> pd.DataFrame:
    rows = [
        {
            "policy_name": "best_historical_action",
            "rule_key": "all_customers",
            "action_id": global_best_action_id,
        }
    ]
    for segment, action_id in heuristic_policy.segment_to_action_id.items():
        rows.append(
            {
                "policy_name": heuristic_policy.name,
                "rule_key": segment,
                "action_id": action_id,
            }
        )
    for segment, action_id in segment_lookup_policy.segment_to_action_id.items():
        rows.append(
            {
                "policy_name": segment_lookup_policy.name,
                "rule_key": segment,
                "action_id": action_id,
            }
        )

    mapping = pd.DataFrame(rows).merge(
        actions_frame[["action_id", "action_name"]],
        on="action_id",
        how="left",
    )
    return mapping.sort_values(["policy_name", "rule_key"]).reset_index(drop=True)


def _build_linear_coefficients_frame(
    policy: LinearRewardPolicy,
    actions_frame: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    for index, action_id in enumerate(policy.action_ids):
        row = {
            "policy_name": policy.name,
            "action_id": int(action_id),
            "intercept": round(float(policy.coefficients[index, 0]), 6),
        }
        for feature_index, feature_name in enumerate(FEATURE_COLUMNS, start=1):
            row[feature_name] = round(float(policy.coefficients[index, feature_index]), 6)
        rows.append(row)

    return pd.DataFrame(rows).merge(
        actions_frame[["action_id", "action_name"]],
        on="action_id",
        how="left",
    )


def _plot_cumulative_reward(policy_round_traces: pd.DataFrame, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5.5))
    for policy_name, frame in policy_round_traces.groupby("policy_name"):
        ax.plot(frame["round_number"], frame["cumulative_reward"], label=policy_name, linewidth=2)
    ax.set_title("Cumulative Reward by Policy")
    ax.set_xlabel("Round")
    ax.set_ylabel("Cumulative Reward")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _plot_policy_total_reward(policy_summary: pd.DataFrame, output_path: Path) -> None:
    ordered = policy_summary.sort_values("total_reward", ascending=False)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(ordered["policy_name"], ordered["total_reward"], color="#2a9d8f")
    ax.set_title("Total Reward by Policy")
    ax.set_ylabel("Total Reward")
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _plot_policy_action_mix(
    policy_action_distribution: pd.DataFrame,
    output_path: Path,
    actions_frame: pd.DataFrame,
) -> None:
    pivot = (
        policy_action_distribution.pivot(
            index="policy_name",
            columns="action_name",
            values="share",
        )
        .fillna(0.0)
        .reindex(columns=actions_frame["action_name"].tolist())
    )
    fig, ax = plt.subplots(figsize=(10, 5.5))
    bottom = np.zeros(len(pivot), dtype=float)
    colors = ["#264653", "#e76f51", "#f4a261", "#2a9d8f", "#8ab17d"]
    for color, action_name in zip(colors, pivot.columns, strict=True):
        values = pivot[action_name].to_numpy(dtype=float)
        ax.bar(pivot.index, values, bottom=bottom, label=action_name, color=color)
        bottom += values
    ax.set_title("Action Mix by Policy")
    ax.set_ylabel("Share of Rounds")
    ax.tick_params(axis="x", rotation=20)
    ax.legend(frameon=False, bbox_to_anchor=(1.02, 1), loc="upper left")
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _render_report(
    policy_summary: pd.DataFrame,
    training_action_summary: pd.DataFrame,
    policy_mapping: pd.DataFrame,
    n_customers: int,
    train_rounds: int,
    eval_rounds: int,
    random_seed: int,
) -> str:
    best_policy = policy_summary.iloc[0]
    runner_up = policy_summary.iloc[1]
    best_gap = best_policy["total_reward"] - runner_up["total_reward"]
    top_training_action = training_action_summary.sort_values("mean_reward", ascending=False).iloc[0]
    heuristic_rules = policy_mapping.loc[policy_mapping["policy_name"] == "segment_heuristic"]
    heuristic_lines = [
        f"- {row.rule_key}: `{row.action_name}`" for row in heuristic_rules.itertuples(index=False)
    ]

    return "\n".join(
        [
            "# Baseline Policy Comparison",
            "",
            f"- Customers per split: {n_customers}",
            f"- Training rounds: {train_rounds}",
            f"- Evaluation rounds: {eval_rounds}",
            f"- Random seed: {random_seed}",
            "",
            "## Evaluation Winner",
            (
                f"- Best total reward: `{best_policy['policy_name']}` "
                f"with {best_policy['total_reward']:.2f}"
            ),
            (
                f"- Runner-up gap: {best_gap:.2f} vs `{runner_up['policy_name']}`"
            ),
            (
                f"- Best conversion rate among evaluated policies: "
                f"{policy_summary.sort_values('conversion_rate', ascending=False).iloc[0]['policy_name']}"
            ),
            "",
            "## Training Data Snapshot",
            (
                f"- Highest mean reward under random logged data: "
                f"`{top_training_action['action_name']}` ({top_training_action['mean_reward']:.2f})"
            ),
            "",
            "## Heuristic Policy Rules",
            *heuristic_lines,
            "",
            "## Files",
            "- `policy_summary.csv` and `policy_round_traces.csv` contain the main comparison outputs.",
            "- `policy_mapping.csv` documents the static and learned segment rules.",
            "- `linear_model_coefficients.csv` contains the per-action ridge coefficients.",
        ]
    )
