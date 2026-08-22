import json
from functools import lru_cache
import joblib
from sqlalchemy import text
from src.ingestion.load_data import get_engine
from api.config import PROJECT_ROOT

@lru_cache(maxsize=1)
def model_bundle():
    return {
        "delivery": joblib.load(PROJECT_ROOT / "models/late_delivery_pipeline.joblib"),
        "delivery_metadata": json.loads((PROJECT_ROOT / "models/late_delivery_metadata.json").read_text()),
        "segmentation": joblib.load(PROJECT_ROOT / "models/customer_segmentation/rfm_cluster_pipeline.joblib"),
        "segmentation_metadata": json.loads((PROJECT_ROOT / "models/customer_segmentation/cluster_metadata.json").read_text()),
        "orders": joblib.load(PROJECT_ROOT / "models/forecasting/orders_forecast_pipeline.joblib"),
        "revenue": joblib.load(PROJECT_ROOT / "models/forecasting/revenue_forecast_pipeline.joblib"),
        "forecast_metadata": json.loads((PROJECT_ROOT / "models/forecasting/forecast_metadata.json").read_text()),
    }

def database_check() -> bool:
    engine = get_engine()
    try:
        with engine.connect() as connection:
            connection.execute(text("SET TRANSACTION READ ONLY"))
            return connection.execute(text("SELECT 1")).scalar_one() == 1
    finally:
        engine.dispose()
