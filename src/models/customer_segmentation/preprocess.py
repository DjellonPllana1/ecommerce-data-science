"""RFM scoring and clustering transformations."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

from .config import RANDOM_STATE

RFM_FEATURES=["recency","frequency","monetary"]


def add_rfm_scores(frame: pd.DataFrame) -> pd.DataFrame:
    """Add interpretable scores and Olist-adapted rule segments."""
    scored=frame.copy()
    scored["r_score"]=pd.qcut(scored["recency"].rank(method="first"),5,labels=[5,4,3,2,1]).astype(int)
    scored["m_score"]=pd.qcut(scored["monetary"].rank(method="first"),5,labels=[1,2,3,4,5]).astype(int)
    scored["f_score"]=np.select([scored.frequency.eq(1),scored.frequency.eq(2),scored.frequency.eq(3),scored.frequency.eq(4),scored.frequency.ge(5)],[1,2,3,4,5],default=1).astype(int)
    conditions=[
        (scored.r_score.ge(4)&scored.f_score.ge(3)&scored.m_score.ge(4)),
        (scored.f_score.ge(3)&scored.r_score.ge(3)),
        (scored.r_score.le(2)&scored.m_score.ge(4)),
        (scored.r_score.eq(5)&scored.f_score.eq(1)),
        (scored.r_score.ge(4)&scored.f_score.eq(2)),
        (scored.r_score.ge(4)&scored.m_score.ge(3)),
        (scored.r_score.le(2)&scored.f_score.ge(2)),
        scored.r_score.eq(3),
        scored.r_score.le(2),
    ]
    names=["Champions","Loyal Customers","High Value At Risk","New Customers","Potential Loyalists","Promising","At Risk","Needs Attention","Hibernating"]
    scored["rfm_segment"]=np.select(conditions,names,default="Promising")
    return scored


def make_cluster_pipeline(k: int) -> Pipeline:
    """Log-transform skewed RFM values, standardize them, and fit KMeans."""
    return Pipeline([
        ("log1p",FunctionTransformer(np.log1p,feature_names_out="one-to-one")),
        ("scaler",StandardScaler()),
        ("kmeans",KMeans(n_clusters=k,n_init=20,random_state=RANDOM_STATE)),
    ])
