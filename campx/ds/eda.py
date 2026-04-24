"""Initial EDA workflow for synthetic retail personalization datasets."""

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
    from .synthetic.config import FEATURE_COLUMNS, LATENT_COLUMNS
except ImportError:  # pragma: no cover - supports running inside the ds container
    from synthetic.config import FEATURE_COLUMNS, LATENT_COLUMNS

REQUIRED_FILES = ("customers.csv", "actions.csv", "interactions.csv")
OPTIONAL_LATENT_FILE = "customer_latents.csv"
SEGMENT_ORDER = ["Champion", "Loyal", "At-Risk", "Lost"]
SEGMENT_COLORS = {
    "Champion": "#1b9e77",
    "Loyal": "#7570b3",
    "At-Risk": "#d95f02",
    "Lost": "#e7298a",
}


@dataclass(slots=True)
class EDAInputs:
    """Input tables loaded from one generated dataset directory."""

    customers: pd.DataFrame
    actions: pd.DataFrame
    interactions: pd.DataFrame
    customer_latents: pd.DataFrame | None


@dataclass(slots=True)
class EDAArtifacts:
    """Output locations and key summary tables from an EDA run."""

    output_dir: Path
    segment_counts: pd.DataFrame
    customer_summary: pd.DataFrame
    segment_feature_means: pd.DataFrame
    action_summary: pd.DataFrame
    feature_correlations: pd.DataFrame
    latent_feature_correlations: pd.DataFrame | None
    report_path: Path
    plot_paths: dict[str, Path]


def load_inputs(input_dir: Path) -> EDAInputs:
    """Load the generated dataset artifacts required for initial EDA."""

    missing = [name for name in REQUIRED_FILES if not (input_dir / name).exists()]
    if missing:
        missing_str = ", ".join(missing)
        raise FileNotFoundError(f"Missing required EDA input files in {input_dir}: {missing_str}")

    customers = pd.read_csv(input_dir / "customers.csv")
    actions = pd.read_csv(input_dir / "actions.csv")
    interactions = pd.read_csv(input_dir / "interactions.csv")

    latents_path = input_dir / OPTIONAL_LATENT_FILE
    customer_latents = pd.read_csv(latents_path) if latents_path.exists() else None

    return EDAInputs(
        customers=customers,
        actions=actions,
        interactions=interactions,
        customer_latents=customer_latents,
    )


def run_eda(
    input_dir: Path,
    output_dir: Path | None = None,
    max_scatter_points: int = 2000,
    random_seed: int = 42,
) -> EDAArtifacts:
    """Run the initial EDA workflow and persist tables, plots, and a short report."""

    dataset_dir = Path(input_dir)
    eda_output_dir = Path(output_dir) if output_dir is not None else dataset_dir / "eda"
    eda_output_dir.mkdir(parents=True, exist_ok=True)

    inputs = load_inputs(dataset_dir)
    segment_counts = _build_segment_counts(inputs.customers)
    customer_summary = inputs.customers[FEATURE_COLUMNS].describe().round(3)
    segment_feature_means = (
        inputs.customers.groupby("segment")[FEATURE_COLUMNS].mean().round(3).reset_index()
    )
    action_summary = _build_action_summary(inputs.interactions, inputs.actions)
    feature_correlations = inputs.customers[FEATURE_COLUMNS].corr().round(3)
    latent_feature_correlations = _build_latent_feature_correlations(
        customers=inputs.customers,
        customer_latents=inputs.customer_latents,
    )

    segment_counts.to_csv(eda_output_dir / "segment_counts.csv", index=False)
    customer_summary.to_csv(eda_output_dir / "customer_summary.csv")
    segment_feature_means.to_csv(eda_output_dir / "segment_feature_means.csv", index=False)
    action_summary.to_csv(eda_output_dir / "action_summary.csv", index=False)
    feature_correlations.to_csv(eda_output_dir / "feature_correlations.csv")
    if latent_feature_correlations is not None:
        latent_feature_correlations.to_csv(eda_output_dir / "latent_feature_correlations.csv")

    plot_paths = {
        "segment_counts": eda_output_dir / "segment_counts.png",
        "customer_feature_histograms": eda_output_dir / "customer_feature_histograms.png",
        "segment_scatter": eda_output_dir / "segment_scatter.png",
        "action_performance": eda_output_dir / "action_performance.png",
        "action_reward_distribution": eda_output_dir / "action_reward_distribution.png",
        "feature_correlations": eda_output_dir / "feature_correlations.png",
    }
    if latent_feature_correlations is not None:
        plot_paths["latent_feature_correlations"] = (
            eda_output_dir / "latent_feature_correlations.png"
        )

    _plot_segment_counts(segment_counts, plot_paths["segment_counts"])
    _plot_customer_feature_histograms(inputs.customers, plot_paths["customer_feature_histograms"])
    _plot_segment_scatter(
        customers=inputs.customers,
        output_path=plot_paths["segment_scatter"],
        max_points=max_scatter_points,
        random_seed=random_seed,
    )
    _plot_action_performance(action_summary, plot_paths["action_performance"])
    _plot_action_reward_distribution(
        interactions=inputs.interactions,
        actions=inputs.actions,
        output_path=plot_paths["action_reward_distribution"],
    )
    _plot_heatmap(
        matrix=feature_correlations,
        output_path=plot_paths["feature_correlations"],
        title="Observed Feature Correlations",
        center_zero=True,
    )
    if latent_feature_correlations is not None:
        _plot_heatmap(
            matrix=latent_feature_correlations,
            output_path=plot_paths["latent_feature_correlations"],
            title="Latent vs Observed Feature Correlations",
            center_zero=True,
        )

    report_path = eda_output_dir / "eda_report.md"
    report_path.write_text(
        _render_report(
            input_dir=dataset_dir,
            customers=inputs.customers,
            interactions=inputs.interactions,
            segment_counts=segment_counts,
            action_summary=action_summary,
            has_latents=inputs.customer_latents is not None,
        )
        + "\n"
    )

    return EDAArtifacts(
        output_dir=eda_output_dir,
        segment_counts=segment_counts,
        customer_summary=customer_summary,
        segment_feature_means=segment_feature_means,
        action_summary=action_summary,
        feature_correlations=feature_correlations,
        latent_feature_correlations=latent_feature_correlations,
        report_path=report_path,
        plot_paths=plot_paths,
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the EDA workflow."""

    parser = argparse.ArgumentParser(
        description="Create an initial EDA report for generated synthetic retail data."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing generated CSV artifacts such as customers.csv and interactions.csv.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Where to write EDA tables and plots. Defaults to <input-dir>/eda.",
    )
    parser.add_argument(
        "--max-scatter-points",
        type=int,
        default=2000,
        help="Maximum number of customer points rendered in the segment scatter plot.",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=42,
        help="Seed used when subsampling points for visualizations.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI entrypoint and print the output location."""

    parser = build_parser()
    args = parser.parse_args(argv)
    artifacts = run_eda(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        max_scatter_points=args.max_scatter_points,
        random_seed=args.random_seed,
    )
    print(f"EDA artifacts written to: {artifacts.output_dir}")
    return 0


def _build_segment_counts(customers: pd.DataFrame) -> pd.DataFrame:
    counts = (
        customers["segment"]
        .value_counts()
        .rename_axis("segment")
        .reset_index(name="count")
    )
    counts["segment"] = pd.Categorical(counts["segment"], SEGMENT_ORDER, ordered=True)
    return counts.sort_values("segment").reset_index(drop=True)


def _build_action_summary(interactions: pd.DataFrame, actions: pd.DataFrame) -> pd.DataFrame:
    merged = interactions.merge(
        actions[["action_id", "action_name"]],
        on="action_id",
        how="left",
    )
    summary = (
        merged.groupby(["action_id", "action_name"], as_index=False)
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
        .sort_values("action_id")
        .reset_index(drop=True)
    )
    return summary


def _build_latent_feature_correlations(
    customers: pd.DataFrame,
    customer_latents: pd.DataFrame | None,
) -> pd.DataFrame | None:
    if customer_latents is None:
        return None

    merged = customers.merge(customer_latents, on="customer_id", how="inner")
    return merged[LATENT_COLUMNS + FEATURE_COLUMNS].corr().loc[LATENT_COLUMNS, FEATURE_COLUMNS].round(3)


def _plot_segment_counts(segment_counts: pd.DataFrame, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = [SEGMENT_COLORS[str(segment)] for segment in segment_counts["segment"]]
    ax.bar(segment_counts["segment"].astype(str), segment_counts["count"], color=colors)
    ax.set_title("Customer Segment Counts")
    ax.set_xlabel("Segment")
    ax.set_ylabel("Customers")
    for index, row in segment_counts.iterrows():
        ax.text(index, row["count"] + 0.5, int(row["count"]), ha="center", va="bottom", fontsize=9)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _plot_customer_feature_histograms(customers: pd.DataFrame, output_path: Path) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    axes_flat = axes.flatten()
    for ax, column in zip(axes_flat, FEATURE_COLUMNS, strict=True):
        ax.hist(customers[column], bins=24, color="#457b9d", edgecolor="white")
        ax.set_title(column.replace("_", " ").title())
        ax.set_ylabel("Count")
    fig.suptitle("Observed Customer Feature Distributions", fontsize=14)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _plot_segment_scatter(
    customers: pd.DataFrame,
    output_path: Path,
    max_points: int,
    random_seed: int,
) -> None:
    rng = np.random.default_rng(random_seed)
    plot_customers = customers
    if len(customers) > max_points:
        sample_indices = rng.choice(len(customers), size=max_points, replace=False)
        plot_customers = customers.iloc[np.sort(sample_indices)].copy()

    fig, ax = plt.subplots(figsize=(9, 6))
    for segment in SEGMENT_ORDER:
        subset = plot_customers.loc[plot_customers["segment"] == segment]
        if subset.empty:
            continue
        ax.scatter(
            subset["recency"],
            subset["monetary"],
            s=np.clip(subset["frequency"] * 8, 18, 150),
            alpha=0.65,
            label=segment,
            color=SEGMENT_COLORS[segment],
            edgecolors="white",
            linewidths=0.3,
        )
    ax.set_title("Segment Scatter: Recency vs Monetary")
    ax.set_xlabel("Recency")
    ax.set_ylabel("Monetary")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _plot_action_performance(action_summary: pd.DataFrame, output_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    action_names = action_summary["action_name"]

    axes[0].bar(action_names, action_summary["mean_conversion_rate"], color="#2a9d8f")
    axes[0].set_title("Mean Conversion Rate by Action")
    axes[0].set_ylabel("Conversion Rate")
    axes[0].tick_params(axis="x", rotation=20)

    axes[1].bar(action_names, action_summary["mean_reward"], color="#e76f51")
    axes[1].set_title("Mean Reward by Action")
    axes[1].set_ylabel("Reward")
    axes[1].tick_params(axis="x", rotation=20)

    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _plot_action_reward_distribution(
    interactions: pd.DataFrame,
    actions: pd.DataFrame,
    output_path: Path,
) -> None:
    merged = interactions.merge(actions[["action_id", "action_name"]], on="action_id", how="left")
    plot_data = [
        merged.loc[merged["action_name"] == action_name, "reward"].to_numpy()
        for action_name in actions.sort_values("action_id")["action_name"]
    ]
    labels = actions.sort_values("action_id")["action_name"].tolist()

    fig, ax = plt.subplots(figsize=(10, 5))
    boxplot = ax.boxplot(
        plot_data,
        patch_artist=True,
        tick_labels=labels,
        showfliers=False,
    )
    for patch in boxplot["boxes"]:
        patch.set_facecolor("#a8dadc")
    ax.set_title("Reward Distribution by Action")
    ax.set_ylabel("Reward")
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _plot_heatmap(
    matrix: pd.DataFrame,
    output_path: Path,
    title: str,
    center_zero: bool,
) -> None:
    values = matrix.to_numpy()
    vmin = -1.0 if center_zero else float(np.nanmin(values))
    vmax = 1.0 if center_zero else float(np.nanmax(values))

    fig, ax = plt.subplots(figsize=(max(6, 0.9 * matrix.shape[1]), max(4, 0.9 * matrix.shape[0])))
    image = ax.imshow(values, cmap="coolwarm", vmin=vmin, vmax=vmax, aspect="auto")
    ax.set_xticks(range(matrix.shape[1]), matrix.columns, rotation=30, ha="right")
    ax.set_yticks(range(matrix.shape[0]), matrix.index)
    ax.set_title(title)

    for row_index in range(matrix.shape[0]):
        for col_index in range(matrix.shape[1]):
            ax.text(
                col_index,
                row_index,
                f"{values[row_index, col_index]:.2f}",
                ha="center",
                va="center",
                color="black",
                fontsize=8,
            )

    fig.colorbar(image, ax=ax, shrink=0.9)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _render_report(
    input_dir: Path,
    customers: pd.DataFrame,
    interactions: pd.DataFrame,
    segment_counts: pd.DataFrame,
    action_summary: pd.DataFrame,
    has_latents: bool,
) -> str:
    top_conversion = action_summary.sort_values(
        ["mean_conversion_rate", "mean_reward"],
        ascending=[False, False],
    ).iloc[0]
    top_reward = action_summary.sort_values("mean_reward", ascending=False).iloc[0]
    segment_lines = [
        f"- {row.segment}: {int(row.count)} customers"
        for row in segment_counts.itertuples(index=False)
    ]

    simulation_count = interactions["simulation_id"].nunique() if "simulation_id" in interactions else 0
    return "\n".join(
        [
            "# Initial EDA Report",
            "",
            f"- Input dataset: `{input_dir}`",
            f"- Customers: {len(customers)}",
            f"- Interactions: {len(interactions)}",
            f"- Distinct simulations: {simulation_count}",
            f"- Latent table available: {'yes' if has_latents else 'no'}",
            "",
            "## Segment Mix",
            *segment_lines,
            "",
            "## Topline Findings",
            (
                f"- Highest mean conversion: `{top_conversion['action_name']}` "
                f"({top_conversion['mean_conversion_rate']:.3f})"
            ),
            (
                f"- Highest mean reward: `{top_reward['action_name']}` "
                f"({top_reward['mean_reward']:.2f})"
            ),
            (
                f"- Mean avg order size: {customers['avg_order_size'].mean():.2f}; "
                f"mean monetary value: {customers['monetary'].mean():.2f}"
            ),
            "",
            "## Output Artifacts",
            "- Summary CSVs: `segment_counts.csv`, `customer_summary.csv`, `segment_feature_means.csv`, `action_summary.csv`, `feature_correlations.csv`",
            "- Plots: `segment_counts.png`, `customer_feature_histograms.png`, `segment_scatter.png`, `action_performance.png`, `action_reward_distribution.png`, `feature_correlations.png`",
            (
                "- Additional latent-aware outputs: `latent_feature_correlations.csv`, "
                "`latent_feature_correlations.png`"
                if has_latents
                else "- Latent-aware outputs were skipped because `customer_latents.csv` was not present."
            ),
        ]
    )
