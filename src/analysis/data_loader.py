"""Reusable PostgreSQL extractors for exploratory analysis.

Every query documents and preserves its analytical grain. Source tables are only
read; payments and order-level reviews are aggregated before downstream joins.
"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.ingestion.load_data import get_engine


ORDERS_SQL = """
-- Grain: one row per order. Payments and freight are aggregated before joining.
WITH order_payments AS (
    SELECT order_id, SUM(payment_value) AS order_value,
           MAX(payment_installments) AS maximum_installments
    FROM payments GROUP BY order_id
), order_freight AS (
    SELECT order_id, SUM(freight_value) AS freight_value
    FROM order_items GROUP BY order_id
)
SELECT o.order_id, c.customer_unique_id, o.order_status,
       o.order_purchase_timestamp AS purchase_timestamp,
       o.order_approved_at AS approved_at,
       o.order_delivered_carrier_date AS delivered_carrier_at,
       o.order_delivered_customer_date AS delivered_customer_at,
       o.order_estimated_delivery_date AS estimated_delivery_at,
       op.order_value, op.maximum_installments,
       COALESCE(offer.freight_value, 0) AS freight_value,
       c.customer_city, c.customer_state
FROM orders o
JOIN customers c USING (customer_id)
LEFT JOIN order_payments op USING (order_id)
LEFT JOIN order_freight offer USING (order_id)
"""

ITEMS_SQL = """
-- Grain: one row per order item. Item price is GMV, not allocated payment revenue.
SELECT i.order_id, i.order_item_id, i.product_id, i.seller_id,
       i.price, i.freight_value, p.product_category_name,
       COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') AS category_english,
       o.order_status
FROM order_items i
JOIN orders o USING (order_id)
JOIN products p USING (product_id)
LEFT JOIN product_category_translation t USING (product_category_name)
"""

REVIEWS_SQL = """
-- Grain: one row per review/order pair; no item join is used here.
SELECT r.review_id, r.order_id, r.review_score,
       r.review_creation_date, r.review_answer_timestamp,
       CASE WHEN o.order_status <> 'delivered' OR o.order_delivered_customer_date IS NULL THEN NULL
            WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN 'late'
            ELSE 'on_time_or_early' END AS delivery_status,
       CASE WHEN o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
            THEN EXTRACT(EPOCH FROM (o.order_delivered_customer_date - o.order_estimated_delivery_date)) / 86400.0
       END AS delivery_delay_days
FROM reviews r JOIN orders o USING (order_id)
"""

CUSTOMERS_SQL = """
-- Grain: one row per customer_unique_id for eligible commercial orders.
WITH order_payments AS (
    SELECT order_id, SUM(payment_value) AS order_value FROM payments GROUP BY order_id
), customer_orders AS (
    SELECT c.customer_unique_id, MIN(o.order_purchase_timestamp) AS first_purchase,
           MAX(o.order_purchase_timestamp) AS last_purchase, COUNT(*) AS order_count,
           SUM(COALESCE(op.order_value, 0)) AS total_spend
    FROM orders o JOIN customers c USING (customer_id)
    LEFT JOIN order_payments op USING (order_id)
    WHERE o.order_status NOT IN ('canceled', 'unavailable')
    GROUP BY c.customer_unique_id
), latest_location AS (
    SELECT DISTINCT ON (c.customer_unique_id) c.customer_unique_id,
           c.customer_state, c.customer_city
    FROM customers c JOIN orders o USING (customer_id)
    WHERE o.order_status NOT IN ('canceled', 'unavailable')
    ORDER BY c.customer_unique_id, o.order_purchase_timestamp DESC
)
SELECT co.*, ll.customer_state, ll.customer_city
FROM customer_orders co JOIN latest_location ll USING (customer_unique_id)
"""

QUALITY_SQL = """
SELECT
  (SELECT COUNT(*) FROM products WHERE product_category_name IS NULL) AS products_missing_category,
  (SELECT COUNT(*) FROM payments WHERE payment_installments = 0) AS zero_installment_payments,
  (SELECT COUNT(*) FROM payments WHERE payment_type = 'not_defined') AS undefined_payment_methods,
  (SELECT COUNT(*) FROM orders WHERE order_status = 'delivered' AND order_delivered_customer_date IS NULL) AS delivered_missing_timestamp
"""


def read_select(query: str, params: Mapping[str, object] | None = None) -> pd.DataFrame:
    """Execute one SELECT query and return its result as a DataFrame."""
    normalized = query.lstrip().lower()
    if not (normalized.startswith("select") or normalized.startswith("with") or normalized.startswith("--")):
        raise ValueError("EDA data loading accepts SELECT/CTE queries only")
    engine = get_engine()
    try:
        with engine.connect() as connection:
            connection.execute(text("SET TRANSACTION READ ONLY"))
            return pd.read_sql_query(text(query), connection, params=params)
    except SQLAlchemyError as exc:
        raise RuntimeError(f"Could not load analytical data from PostgreSQL: {exc}") from exc
    finally:
        engine.dispose()


def load_analytical_datasets() -> dict[str, pd.DataFrame]:
    """Load the four grain-safe analytical DataFrames and quality counters."""
    return {
        "orders": read_select(ORDERS_SQL),
        "items": read_select(ITEMS_SQL),
        "reviews": read_select(REVIEWS_SQL),
        "customers": read_select(CUSTOMERS_SQL),
        "quality": read_select(QUALITY_SQL),
    }
