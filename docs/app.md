# Frontend | Streamlit

## Overview

The frontend is a Streamlit app for simulation launch, interaction monitoring,
analytics, and model inspection.

App URL:

```text
http://localhost:8501
```

## Main pages

| Page | Purpose |
|------|---------|
| Home | Project overview and navigation |
| Create Simulation | Launch and review simulation runs |
| Interaction | Watch reward and recent decisions |
| Analytics | Review distributions and policy results |
| Model | Inspect learned weights and action scores |

## Frontend reference

### `bandit_utils.py`

::: campx.app.bandit_utils

## Notes

- The current UI structure is in place.
- The main remaining frontend work is full live API integration and removal of mock-only behavior.
