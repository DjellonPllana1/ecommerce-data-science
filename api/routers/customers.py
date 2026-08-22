import pandas as pd
from fastapi import APIRouter,HTTPException
from api.dependencies import model_bundle
from api.schemas import SegmentRequest,SegmentResponse
router=APIRouter(prefix='/predict',tags=['prediction'])
@router.post('/customer-segment',response_model=SegmentResponse)
def segment(payload:SegmentRequest):
    try:
        b=model_bundle(); label=int(b['segmentation'].predict(pd.DataFrame([payload.model_dump()]))[0]); return SegmentResponse(cluster_id=label,cluster_name=b['segmentation_metadata']['cluster_names'][str(label)])
    except Exception as exc: raise HTTPException(500,f'Segmentation failed: {exc}') from exc
