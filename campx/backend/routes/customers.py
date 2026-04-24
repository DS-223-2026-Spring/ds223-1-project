from fastapi import APIRouter

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("/")
def get_customers():
    return {"message": "not implemented yet — M3"}


@router.get("/{customer_id}")
def get_customer(customer_id: int):
    return {"message": "not implemented yet — M3", "customer_id": customer_id}
