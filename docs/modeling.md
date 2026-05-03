# Data Science | Modeling

## Overview

The DS layer generates synthetic customer data, runs LinUCB, compares it
against baseline policies, and exports final artifacts for the rest of the
system.

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
  --output-dir outputs/final_outputs
```

Other useful entrypoints:

```bash
python -m campx.ds.generate_synthetic_data --output-dir outputs/synthetic_data
python -m campx.ds.generate_final_outputs --input-dir outputs/synthetic_data --output-dir outputs/final_outputs
python -m campx.ds.generate_eda_report --input-dir outputs/final_outputs --output-dir outputs/final_outputs/eda
```

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

