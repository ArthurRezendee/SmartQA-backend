
from fastapi import APIRouter
from app.modules.billing.controller.billing_controller import BillingController

router = APIRouter(
    prefix="/billing",
    tags=["Billing"]
)

controller = BillingController()


@router.get("/")
async def index():
    return await controller.index()
