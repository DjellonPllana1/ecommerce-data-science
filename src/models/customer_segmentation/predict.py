"""Assign persisted KMeans clusters to customer RFM values."""

from __future__ import annotations

import json
from collections.abc import Mapping

import joblib
import pandas as pd

from .config import METADATA_PATH,PIPELINE_PATH
from .preprocess import RFM_FEATURES


def predict_segment(customers: pd.DataFrame|Mapping[str,object]) -> pd.DataFrame:
    frame=pd.DataFrame([customers]) if isinstance(customers,Mapping) else customers.copy(); missing=set(RFM_FEATURES)-set(frame.columns)
    if missing: raise ValueError(f"Missing RFM fields: {sorted(missing)}")
    if (frame[RFM_FEATURES]<0).any().any(): raise ValueError("RFM values must be non-negative")
    pipeline=joblib.load(PIPELINE_PATH); metadata=json.loads(METADATA_PATH.read_text(encoding="utf-8")); labels=pipeline.predict(frame[RFM_FEATURES]); names={int(k):v for k,v in metadata["cluster_names"].items()}
    return pd.DataFrame({"cluster_id":labels,"cluster_name":[names[int(label)] for label in labels]},index=frame.index)
