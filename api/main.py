"""FastAPI main entry point."""
from fastapi import FastAPI

app = FastAPI(title="Campaign Optimization Engine", version="0.1.0")

@app.get("/health")
def health_check():
    return {"status": "ok"}

# TODO (M3): POST /decide
# TODO (M3): POST /feedback
# TODO (M3): GET /metrics
