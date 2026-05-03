# Docker

## Services

The project runs as a multi-container stack with Docker Compose.

| Service | Purpose | URL |
|--------|---------|-----|
| `front` | Streamlit dashboard | `http://localhost:8501` |
| `backend` | FastAPI API + Swagger | `http://localhost:8000/docs` |
| `db` | PostgreSQL database | internal on `5432` |
| `pgadmin` | Database browser | `http://localhost:5050` |
| `campaign_ds` | Data science workflow container | writes artifacts and exits |

## Start the stack

```bash
docker compose up --build
```

## Stop the stack

```bash
docker compose down
```

## Notes

- From your browser, use `localhost`.
- Inside Docker containers, services talk to each other by Compose service name.
- Example: the frontend container reaches the API at `http://backend:8000`.

## Main compose file

```text
docker-compose.yml
```
