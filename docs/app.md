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
| Customers | View and filter customer profiles |

## Frontend reference

### `bandit_utils.py`

::: campx.app.bandit_utils

## Notes

- The current UI structure is in place.
- The Streamlit app is fully wired to the live FastAPI backend (mocks removed).
