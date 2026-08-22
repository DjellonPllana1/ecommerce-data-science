"""Load persisted artifacts and generate supported future horizons."""
from __future__ import annotations
import json,joblib,numpy as np,pandas as pd
from .baselines import baseline_forecast
from .config import HORIZONS,METADATA_PATH,ORDERS_MODEL_PATH,REVENUE_MODEL_PATH
from .features import recursive_model_forecast
def _predict(artifact,horizon):
    return baseline_forecast(artifact["model_name"],artifact["history"],horizon) if artifact["kind"]=="baseline" else recursive_model_forecast(artifact["model"],artifact["history"],horizon)
def generate_forecast(horizon:int=30)->pd.DataFrame:
    if horizon not in HORIZONS: raise ValueError(f"Supported horizons: {HORIZONS}")
    orders=joblib.load(ORDERS_MODEL_PATH); revenue=joblib.load(REVENUE_MODEL_PATH); metadata=json.loads(METADATA_PATH.read_text()); op=_predict(orders,horizon); rp=_predict(revenue,horizon); steps=np.arange(1,horizon+1); scale=np.sqrt(1+steps/7)
    oq=metadata["uncertainty"]["orders"]; rq=metadata["uncertainty"]["revenue"]
    return pd.DataFrame({"date":op.index,"predicted_orders":op.values,"predicted_revenue":rp.values,"orders_lower_bound":np.maximum(0,op.values+oq[0]*scale),"orders_upper_bound":op.values+oq[1]*scale,"revenue_lower_bound":np.maximum(0,rp.values+rq[0]*scale),"revenue_upper_bound":rp.values+rq[1]*scale})
