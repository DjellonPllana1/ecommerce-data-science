"""Build the one-order-per-row late-delivery modeling dataset from PostgreSQL."""

from __future__ import annotations

import pandas as pd

from src.analysis.data_loader import read_select
from .config import IDENTIFIER, TARGET, TIME_COLUMN

MODELING_SQL = """
-- Grain: exactly one row per delivered order with a known delivery outcome.
WITH item_detail AS (
    SELECT i.order_id, i.product_id, i.seller_id, i.price, i.freight_value,
           p.product_weight_g, p.product_length_cm, p.product_height_cm, p.product_width_cm,
           COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') AS category,
           s.seller_state
    FROM order_items i JOIN products p USING (product_id) JOIN sellers s USING (seller_id)
    LEFT JOIN product_category_translation t USING (product_category_name)
), item_agg AS (
    SELECT order_id, SUM(price) AS item_value, SUM(freight_value) AS freight_value,
           COUNT(*) AS item_count, COUNT(DISTINCT product_id) AS unique_products,
           COUNT(DISTINCT seller_id) AS seller_count, SUM(product_weight_g) AS total_product_weight_g,
           AVG(product_length_cm) AS average_product_length_cm,
           AVG(product_height_cm) AS average_product_height_cm,
           AVG(product_width_cm) AS average_product_width_cm
    FROM item_detail GROUP BY order_id
), category_rank AS (
    SELECT order_id, category,
           ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY COUNT(*) DESC, category) AS rank
    FROM item_detail GROUP BY order_id, category
), seller_state_rank AS (
    SELECT order_id, seller_state,
           ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY COUNT(*) DESC, seller_state) AS rank
    FROM item_detail GROUP BY order_id, seller_state
), payment_detail AS (
    SELECT order_id, payment_type, SUM(payment_value) AS type_value,
           MAX(payment_installments) AS type_installments
    FROM payments GROUP BY order_id, payment_type
), payment_rank AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY type_value DESC, payment_type) AS rank
    FROM payment_detail
), payment_agg AS (
    SELECT order_id, SUM(type_value) AS payment_value, MAX(type_installments) AS payment_installments
    FROM payment_detail GROUP BY order_id
)
SELECT o.order_id, o.order_purchase_timestamp AS purchase_timestamp,
       EXTRACT(MONTH FROM o.order_purchase_timestamp)::int AS purchase_month,
       EXTRACT(ISODOW FROM o.order_purchase_timestamp)::int AS purchase_day_of_week,
       EXTRACT(HOUR FROM o.order_purchase_timestamp)::int AS purchase_hour,
       c.customer_state, FLOOR(c.customer_zip_code_prefix / 1000.0)::int AS customer_zip_region,
       ia.item_value, ia.freight_value, ia.item_count, ia.unique_products, ia.seller_count,
       ia.total_product_weight_g, ia.average_product_length_cm,
       ia.average_product_height_cm, ia.average_product_width_cm,
       cr.category AS dominant_product_category, ssr.seller_state AS dominant_seller_state,
       CASE WHEN c.customer_state = ssr.seller_state THEN 'yes' ELSE 'no' END AS same_customer_seller_state,
       pr.payment_type, pa.payment_value, pa.payment_installments,
       EXTRACT(EPOCH FROM (o.order_estimated_delivery_date - o.order_purchase_timestamp)) / 86400.0 AS estimated_delivery_window_days,
       CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN 1 ELSE 0 END AS is_late_delivery
FROM orders o JOIN customers c ON c.customer_id = o.customer_id
JOIN item_agg ia ON ia.order_id = o.order_id
LEFT JOIN category_rank cr ON cr.order_id = o.order_id AND cr.rank = 1
LEFT JOIN seller_state_rank ssr ON ssr.order_id = o.order_id AND ssr.rank = 1
LEFT JOIN payment_agg pa ON pa.order_id = o.order_id
LEFT JOIN payment_rank pr ON pr.order_id = o.order_id AND pr.rank = 1
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
  AND o.order_estimated_delivery_date IS NOT NULL
ORDER BY o.order_purchase_timestamp, o.order_id
"""


def build_modeling_dataset() -> pd.DataFrame:
    """Load, validate, and return the chronological modeling dataset."""
    frame = read_select(MODELING_SQL)
    frame[TIME_COLUMN] = pd.to_datetime(frame[TIME_COLUMN], errors="raise")
    frame[TARGET] = frame[TARGET].astype("int8")
    if frame[IDENTIFIER].duplicated().any():
        raise ValueError("Modeling dataset violates one-row-per-order grain")
    if not frame[TARGET].isin([0, 1]).all():
        raise ValueError("Target contains values outside {0, 1}")
    return frame


if __name__ == "__main__":
    dataset = build_modeling_dataset()
    positives = int(dataset[TARGET].sum())
    print(f"Rows: {len(dataset):,}")
    print(f"Late: {positives:,}; on time/early: {len(dataset)-positives:,}")
    print(f"Late prevalence: {dataset[TARGET].mean():.4%}")
