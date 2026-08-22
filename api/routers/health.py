from fastapi import APIRouter
from api.dependencies import database_check, model_bundle
from api.schemas import HealthResponse

router = APIRouter(tags=["health"])

@router.get("/health", response_model=HealthResponse)
def health():
    try: db = database_check()
    except Exception: db = False
    try: bundle = model_bundle()
    except Exception: bundle = {}
    return HealthResponse(api_status="ok" if db else "degraded", database_connected=db,
        late_delivery_model_available="delivery" in bundle, segmentation_model_available="segmentation" in bundle,
        orders_forecast_model_available="orders" in bundle, revenue_forecast_model_available="revenue" in bundle)
