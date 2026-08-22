"""Shared configuration for late-delivery modeling."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MODEL_DIR = PROJECT_ROOT / "models"
REPORT_DIR = PROJECT_ROOT / "reports" / "modeling"
FIGURE_DIR = REPORT_DIR / "figures"
MODEL_PATH = MODEL_DIR / "late_delivery_pipeline.joblib"
METADATA_PATH = MODEL_DIR / "late_delivery_metadata.json"
RANDOM_STATE = 42

NUMERIC_FEATURES = [
    "purchase_month", "purchase_day_of_week", "purchase_hour",
    "customer_zip_region", "item_value", "freight_value", "item_count",
    "unique_products", "seller_count", "total_product_weight_g",
    "average_product_length_cm", "average_product_height_cm",
    "average_product_width_cm", "payment_value", "payment_installments",
    "estimated_delivery_window_days",
]
CATEGORICAL_FEATURES = [
    "customer_state", "dominant_product_category", "dominant_seller_state",
    "same_customer_seller_state", "payment_type",
]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
TARGET = "is_late_delivery"
IDENTIFIER = "order_id"
TIME_COLUMN = "purchase_timestamp"

PROHIBITED_FEATURES = {
    "order_delivered_customer_date", "order_delivered_carrier_date",
    "delivered_customer_at", "delivered_carrier_at", "delivery_days",
    "delivery_delay_days", "review_score", "review_comment_title",
    "review_comment_message", "review_creation_date", "review_answer_timestamp",
    TARGET,
}
