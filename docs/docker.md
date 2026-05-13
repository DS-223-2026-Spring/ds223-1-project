# Docker / Local Run

## Services

The project runs as a multi-container stack with Docker Compose.

| Service | Purpose | URL |
|--------|---------|-----|
| `front` | Streamlit dashboard | `http://localhost:8501` |
| `backend` | FastAPI API and Swagger | `http://localhost:8000/docs` |
| `db` | PostgreSQL database | internal on `5432` |
| `pgadmin` | Database browser | `http://localhost:5050` |
| `campaign_ds` | DS workflow — generates data, runs LinUCB, persists artifacts | exits with code 0 when done |

The `campaign_ds` container is a batch job. It generates synthetic customers, runs the campaign simulation, and persists all outputs to PostgreSQL, then exits with code 0. This is expected behavior, not a failure.

## Start the Stack

```bash
docker compose up --build
```

## Stop the Stack

```bash
docker compose down
```

To also remove volumes (database data):

```bash
docker compose down -v
```

## Health Check

```bash
curl http://localhost:8000/health
```

Expected: `{"status":"ok","service":"backend"}`

## Notes

- From your browser, use `localhost`.
- Inside Docker containers, services communicate by Compose service name (e.g., `http://backend:8000`).
- If the build fails with a snapshot error, run `docker builder prune -f` then rebuild.
- The compose file is `docker-compose.yml` in the repo root.
