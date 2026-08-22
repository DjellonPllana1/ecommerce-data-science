"""Leakage-safe feature definitions and scikit-learn preprocessing."""

from __future__ import annotations

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .config import CATEGORICAL_FEATURES, FEATURES, NUMERIC_FEATURES, PROHIBITED_FEATURES

FEATURE_AUDIT = {
    "purchase_month": "Known from purchase timestamp.",
    "purchase_day_of_week": "Known from purchase timestamp.",
    "purchase_hour": "Known from purchase timestamp.",
    "customer_state": "Shipping/customer location known at purchase.",
    "customer_zip_region": "Coarse region derived from the known customer ZIP prefix.",
    "item_value": "Sum of ordered item prices known at purchase.",
    "freight_value": "Quoted order-item freight known at purchase.",
    "item_count": "Basket composition known at purchase.",
    "unique_products": "Basket composition known at purchase.",
    "seller_count": "Sellers fulfilling the basket are known at purchase.",
    "total_product_weight_g": "Catalog attributes known before fulfillment.",
    "average_product_length_cm": "Catalog attributes known before fulfillment.",
    "average_product_height_cm": "Catalog attributes known before fulfillment.",
    "average_product_width_cm": "Catalog attributes known before fulfillment.",
    "dominant_product_category": "Category of ordered products known at purchase.",
    "dominant_seller_state": "Registered seller location known at purchase.",
    "same_customer_seller_state": "Derived only from known customer/seller states.",
    "payment_type": "Chosen during checkout.",
    "payment_value": "Order payment total known shortly after purchase.",
    "payment_installments": "Checkout payment plan known at purchase.",
    "estimated_delivery_window_days": "Platform estimate shown at purchase; no actual delivery data.",
}


def audit_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Fail if a prohibited or undocumented field enters the feature matrix."""
    selected = set(FEATURES)
    leakage = selected & PROHIBITED_FEATURES
    undocumented = selected - set(FEATURE_AUDIT)
    missing = selected - set(frame.columns)
    if leakage or undocumented or missing:
        raise ValueError(f"Feature audit failed: leakage={leakage}, undocumented={undocumented}, missing={missing}")
    return pd.DataFrame([{"feature": feature, "available_at_prediction_time": True, "rationale": FEATURE_AUDIT[feature]} for feature in FEATURES])


def build_preprocessor(scale_numeric: bool) -> ColumnTransformer:
    """Create train-fitted numeric and categorical transformations."""
    numeric_steps = [("imputer", SimpleImputer(strategy="median"))]
    if scale_numeric:
        numeric_steps.append(("scaler", StandardScaler()))
    numeric = Pipeline(numeric_steps)
    categorical = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])
    return ColumnTransformer([
        ("numeric", numeric, NUMERIC_FEATURES),
        ("categorical", categorical, CATEGORICAL_FEATURES),
    ], verbose_feature_names_out=False)
