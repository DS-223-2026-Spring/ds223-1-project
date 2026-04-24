"""Action metadata helpers."""

from __future__ import annotations

import pandas as pd

from .config import ActionCalibration, GeneratorCalibration


def get_action_definitions(
    calibration: GeneratorCalibration,
) -> tuple[ActionCalibration, ...]:
    """Return the canonical action set from the central calibration config."""

    return calibration.actions


def actions_to_frame(actions: tuple[ActionCalibration, ...]) -> pd.DataFrame:
    """Return export-ready action metadata."""

    return pd.DataFrame(
        [
            {
                "action_id": action.action_id,
                "action_name": action.action_name,
                "description": action.description,
                "base_cost": round(action.base_cost, 2),
            }
            for action in actions
        ]
    )
