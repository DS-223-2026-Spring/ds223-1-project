"""Online LinUCB policy for contextual promotion selection."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd

try:
    from ._routing import load_ds_attr
except ImportError:  # pragma: no cover - supports direct execution in DS container
    from _routing import load_ds_attr

build_context_matrix = load_ds_attr("synthetic.features", "build_context_matrix")


@dataclass(frozen=True, slots=True)
class LinUCBScore:
    """Per-action score components for one customer context."""

    action_id: int
    action_name: str
    exploit_score: float
    explore_score: float
    ucb_score: float
    n_pulls: int


@dataclass(slots=True)
class LinUCBPolicy:
    """Disjoint linear UCB with one ridge model per action."""

    alpha: float
    action_ids: np.ndarray
    action_names: dict[int, str]
    feature_columns: tuple[str, ...]
    feature_means: np.ndarray
    feature_scales: np.ndarray
    a_matrices: dict[int, np.ndarray]
    b_vectors: dict[int, np.ndarray]
    n_pulls: dict[int, int]

    @classmethod
    def from_customer_frame(
        cls,
        customer_frame: pd.DataFrame,
        actions: Sequence[object],
        alpha: float,
        feature_columns: Sequence[str],
    ) -> "LinUCBPolicy":
        """Initialize a policy using observed customer features for scaling."""

        feature_matrix = build_context_matrix(
            customers=customer_frame,
            feature_columns=feature_columns,
        )
        feature_means = np.zeros(feature_matrix.shape[1], dtype=float)
        feature_scales = np.max(np.abs(feature_matrix), axis=0)
        feature_scales = np.where(feature_scales < 1e-8, 1.0, feature_scales)

        action_ids = np.array([action.action_id for action in actions], dtype=int)
        action_names = {
            int(action.action_id): str(action.action_name)
            for action in actions
        }
        context_dim = len(feature_columns)

        return cls(
            alpha=float(alpha),
            action_ids=action_ids,
            action_names=action_names,
            feature_columns=tuple(feature_columns),
            feature_means=feature_means,
            feature_scales=feature_scales,
            a_matrices={
                int(action_id): np.eye(context_dim, dtype=float)
                for action_id in action_ids
            },
            b_vectors={
                int(action_id): np.zeros(context_dim, dtype=float)
                for action_id in action_ids
            },
            n_pulls={int(action_id): 0 for action_id in action_ids},
        )

    def transform_frame(self, customer_frame: pd.DataFrame) -> np.ndarray:
        """Return scaled context vectors in the configured feature order."""

        features = build_context_matrix(
            customers=customer_frame,
            feature_columns=self.feature_columns,
        )
        return (features - self.feature_means) / self.feature_scales

    def score_context(self, context: np.ndarray) -> list[LinUCBScore]:
        """Score all actions for one scaled context vector."""

        scores: list[LinUCBScore] = []
        for action_id in self.action_ids:
            action_key = int(action_id)
            a_matrix = self.a_matrices[action_key]
            b_vector = self.b_vectors[action_key]
            theta = np.linalg.solve(a_matrix, b_vector)
            exploit = float(theta @ context)
            uncertainty = float(context @ np.linalg.solve(a_matrix, context))
            explore = float(self.alpha * np.sqrt(max(uncertainty, 0.0)))
            scores.append(
                LinUCBScore(
                    action_id=action_key,
                    action_name=self.action_names[action_key],
                    exploit_score=exploit,
                    explore_score=explore,
                    ucb_score=exploit + explore,
                    n_pulls=self.n_pulls[action_key],
                )
            )
        return scores

    def select_action(self, context: np.ndarray) -> LinUCBScore:
        """Select the highest-UCB action for one scaled context vector."""

        scores = self.score_context(context)
        best_index = int(np.argmax([score.ucb_score for score in scores]))
        return scores[best_index]

    def update(self, action_id: int, context: np.ndarray, reward: float) -> None:
        """Update the selected action arm with its observed reward."""

        action_key = int(action_id)
        self.a_matrices[action_key] += np.outer(context, context)
        self.b_vectors[action_key] += float(reward) * context
        self.n_pulls[action_key] += 1

    def to_model_state_frame(
        self,
        simulation_id: str,
        policy_mode: str,
    ) -> pd.DataFrame:
        """Serialize learned per-action state for CSV and DB persistence."""

        rows = []
        for action_id in self.action_ids:
            action_key = int(action_id)
            a_matrix = self.a_matrices[action_key]
            b_vector = self.b_vectors[action_key]
            theta = np.linalg.solve(a_matrix, b_vector)
            rows.append(
                {
                    "simulation_id": simulation_id,
                    "policy_mode": policy_mode,
                    "action_id": action_key,
                    "action_name": self.action_names[action_key],
                    "alpha": self.alpha,
                    "context_dim": len(self.feature_columns),
                    "n_pulls": self.n_pulls[action_key],
                    "theta_json": json.dumps(theta.tolist()),
                    "a_json": json.dumps(a_matrix.tolist()),
                    "b_json": json.dumps(b_vector.tolist()),
                    "feature_columns_json": json.dumps(list(self.feature_columns)),
                    "feature_means_json": json.dumps(self.feature_means.tolist()),
                    "feature_scales_json": json.dumps(self.feature_scales.tolist()),
                    "context_encoding": "max_scaled_observed_features",
                }
            )
        return pd.DataFrame(rows)
