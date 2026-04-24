from fastapi import APIRouter

router = APIRouter(prefix="", tags=["bandit"])


@router.post("/decide")
def decide(customer_id: int):
    return {"message": "not implemented yet — M3", "customer_id": customer_id}


@router.post("/feedback")
def feedback(interaction_id: int, converted: bool, revenue: float):
    return {"message": "not implemented yet — M3"}


@router.get("/metrics")
def get_metrics(simulation_id: int):
    return {"message": "not implemented yet — M3"}
