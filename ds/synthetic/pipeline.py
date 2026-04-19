"""End-to-end synthetic data pipeline orchestration."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .actions import actions_to_frame, get_action_definitions
from .config import SyntheticDataConfig
from .export import export_artifacts
from .features import generate_observed_features
from .latents import generate_latent_traits
from .simulate import simulate_interactions
from .validate import ValidationArtifacts, build_validation_artifacts


@dataclass(slots=True)
class SyntheticArtifacts:
    """In-memory outputs of one synthetic generation run."""

    customers: pd.DataFrame
    customer_latents: pd.DataFrame
    actions: pd.DataFrame
    interactions: pd.DataFrame
    model_state: pd.DataFrame
    validation: ValidationArtifacts


def run_pipeline(config: SyntheticDataConfig) -> SyntheticArtifacts:
    """Run the standalone synthetic dataset generation pipeline."""

    rng = np.random.default_rng(config.random_seed)
    action_definitions = get_action_definitions(config.calibration)

    customer_latents = generate_latent_traits(
        config.n_customers,
        config.calibration,
        rng,
    )
    customers = generate_observed_features(
        customer_latents,
        config.calibration,
        rng,
    )
    actions = actions_to_frame(action_definitions)
    interactions, model_state = simulate_interactions(
        customers=customers,
        latents=customer_latents,
        actions=action_definitions,
        config=config,
        rng=rng,
    )

    validation = build_validation_artifacts(
        customers=customers,
        latents=customer_latents,
        actions=actions,
        interactions=interactions,
        config=config,
    )
    export_artifacts(
        output_dir=config.output_dir,
        config=config,
        customers=customers,
        customer_latents=customer_latents,
        actions=actions,
        interactions=interactions,
        model_state=model_state,
        validation=validation,
    )

    return SyntheticArtifacts(
        customers=customers,
        customer_latents=customer_latents,
        actions=actions,
        interactions=interactions,
        model_state=model_state,
        validation=validation,
    )
