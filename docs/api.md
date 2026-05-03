# Backend | FastAPI

## Overview

The backend is a FastAPI service that exposes the project API, database-backed
simulation endpoints, DS artifact import routes, and model inspection routes.

Base URL:

```text
http://localhost:8000
```

Swagger:

```text
http://localhost:8000/docs
```

DS generated data can be imported with `POST /ds/artifacts` and retrieved with
`GET /ds/artifacts/{simulation_id}` or
`GET /ds/artifacts/{simulation_id}/{artifact_name}`.

## API Reference

### `main.py`

::: campx.api.main

### `schemas.py`

::: campx.api.schemas

### `crud.py`

::: campx.api.crud