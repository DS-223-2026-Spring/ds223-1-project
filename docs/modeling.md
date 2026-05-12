# Data Science | Modeling

## Overview

The DS layer generates synthetic customer data, runs LinUCB, compares it
against baseline policies, and stores generated run artifacts in PostgreSQL for
the rest of the system.

The detailed feature and reward contract is documented in
[DS Feature & Reward Spec](ds_data_spec.md).

## Main workflow

Repeatable end-to-end run:

```bash
python -m campx.ds.run_workflow \
  --n-customers 500 \
  --n-rounds 5000 \
  --random-seed 42 \
  --policy-mode linucb \
  --output-dir outputs/final_outputs \
  --storage db
```

Other useful entrypoints:

```bash
python -m campx.ds.generate_synthetic_data --storage db
python -m campx.ds.generate_synthetic_data --storage csv --output-dir outputs/synthetic_data
python -m campx.ds.generate_final_outputs --input-dir outputs/synthetic_data --output-dir outputs/final_outputs
python -m campx.ds.generate_eda_report --input-dir outputs/final_outputs --output-dir outputs/final_outputs/eda
python -m campx.ds.verify_reproducibility
```

`--storage db` still writes the generated CSV/report directory first, then loads
those files into PostgreSQL. For the full workflow this includes
`baselines/policy_round_traces.csv`, which is the artifact the backend uses to
add baseline policy columns to `/metrics.cumulative_reward_series`.

`generate_synthetic_data --storage db` is the lightweight synthetic-data import
path. Use `run_workflow --storage db` for the full dashboard/demo path because it
also generates and imports baseline comparison artifacts.

## Reproducibility check

Issue #114 is covered by a dedicated verifier:

```bash
python -m campx.ds.verify_reproducibility
```

The verifier runs `campx.ds.run_workflow` twice with the same seed into temporary
directories and compares deterministic artifacts byte-for-byte. CSV, JSON, text,
and Markdown outputs must match. PNG files are skipped by default because
Matplotlib can write environment-specific image metadata even when the chart is
visually unchanged.

Use the full demo-sized parameters before release:

```bash
python -m campx.ds.verify_reproducibility \
  --n-customers 500 \
  --n-rounds 5000 \
  --baseline-n-customers 500 \
  --baseline-train-rounds 5000 \
  --baseline-eval-rounds 5000 \
  --random-seed 42
```

The verifier intentionally uses local CSV artifact output. DB reproducibility is
then driven from the same deterministic directory by `run_workflow --storage db`.

## Main modules

### `run_workflow.py`

::: campx.ds.run_workflow

### `linucb.py`

::: campx.ds.linucb

### `baselines.py`

::: campx.ds.baselines

### `final_outputs.py`

::: campx.ds.final_outputs

### `model.py`

::: campx.ds.model
