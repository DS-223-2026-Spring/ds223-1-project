from fastapi import APIRouter

router = APIRouter(prefix="/simulations", tags=["simulations"])


@router.get("/")
def list_simulations():
    return {"message": "not implemented yet — M3"}


@router.post("/")
def run_simulation(sim_name: str, num_rounds: int = 1000, alpha: float = 0.5):
    return {"message": "not implemented yet — M3"}
