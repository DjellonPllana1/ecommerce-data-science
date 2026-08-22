import numpy as np, pandas as pd
from fastapi import APIRouter, HTTPException
from api.dependencies import model_bundle
from api.schemas import LateDeliveryRequest,LateDeliveryResponse

router=APIRouter(prefix='/predict',tags=['prediction'])
@router.post('/late-delivery',response_model=LateDeliveryResponse)
def predict(payload:LateDeliveryRequest):
    try:
        b=model_bundle(); frame=pd.DataFrame([payload.model_dump()]); probability=float(b['delivery'].predict_proba(frame[b['delivery_metadata']['features']])[:,1][0]); threshold=float(b['delivery_metadata']['threshold'])
        risk='high' if probability>=threshold else ('medium' if probability>=threshold/2 else 'low'); descriptions={'low':'Low predicted late-delivery risk','medium':'Moderate predicted late-delivery risk','high':'High predicted late-delivery risk'}
        if not np.isfinite(probability) or not 0<=probability<=1: raise RuntimeError('Invalid probability')
        return LateDeliveryResponse(late_delivery_probability=probability,predicted_class=int(probability>=threshold),risk_level=risk,interpretation=descriptions[risk])
    except Exception as exc: raise HTTPException(500,f'Prediction failed: {exc}') from exc
