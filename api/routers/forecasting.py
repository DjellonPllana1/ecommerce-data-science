import numpy as np,pandas as pd
from fastapi import APIRouter,HTTPException,Query
from api.config import settings
from api.dependencies import model_bundle
from api.schemas import ForecastResponse
from src.models.forecasting.baselines import baseline_forecast
from src.models.forecasting.features import recursive_model_forecast
router=APIRouter(tags=['forecasting'])
def run(a,h): return baseline_forecast(a['model_name'],a['history'],h) if a['kind']=='baseline' else recursive_model_forecast(a['model'],a['history'],h)
@router.get('/forecast',response_model=ForecastResponse)
def forecast(horizon:int=Query(7)):
    if horizon not in (7,14,30): raise HTTPException(422,'horizon must be one of 7, 14, or 30')
    try:
        b=model_bundle(); op,rp=run(b['orders'],horizon),run(b['revenue'],horizon); scale=np.sqrt(1+np.arange(1,horizon+1)/7); oq=b['forecast_metadata']['uncertainty']['orders'];rq=b['forecast_metadata']['uncertainty']['revenue']
        frame=pd.DataFrame({'date':op.index,'predicted_orders':op.values,'predicted_revenue':rp.values,'orders_lower_bound':np.maximum(0,op.values+oq[0]*scale),'orders_upper_bound':op.values+oq[1]*scale,'revenue_lower_bound':np.maximum(0,rp.values+rq[0]*scale),'revenue_upper_bound':rp.values+rq[1]*scale})
        return ForecastResponse(horizon=horizon,interval_type=settings.planning_interval_note,forecasts=frame.to_dict('records'))
    except Exception as exc: raise HTTPException(500,f'Forecast failed: {exc}') from exc
