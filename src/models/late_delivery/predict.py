"""Inference interface for the persisted late-delivery pipeline."""

from __future__ import annotations

import json
from collections.abc import Mapping

import joblib
import numpy as np
import pandas as pd

from .config import FEATURES, METADATA_PATH, MODEL_PATH


def predict_late_delivery(orders: pd.DataFrame | Mapping[str, object]) -> pd.DataFrame:
    """Return probability, thresholded class, and LOW/MEDIUM/HIGH risk label."""
    frame=pd.DataFrame([orders]) if isinstance(orders,Mapping) else orders.copy()
    missing=set(FEATURES)-set(frame.columns)
    if missing: raise ValueError(f"Prediction input is missing features: {sorted(missing)}")
    pipeline=joblib.load(MODEL_PATH); metadata=json.loads(METADATA_PATH.read_text(encoding="utf-8")); threshold=float(metadata["threshold"])
    probability=pipeline.predict_proba(frame[FEATURES])[:,1]
    if np.any((probability<0)|(probability>1)): raise RuntimeError("Model returned invalid probabilities")
    risk=np.where(probability>=threshold,"HIGH",np.where(probability>=threshold/2,"MEDIUM","LOW"))
    return pd.DataFrame({"late_delivery_probability":probability,"predicted_late_delivery":(probability>=threshold).astype(int),"risk_label":risk},index=frame.index)


if __name__ == "__main__":
    from .build_dataset import build_modeling_dataset
    examples=build_modeling_dataset().tail(5)
    print(predict_late_delivery(examples).to_string(index=False))
