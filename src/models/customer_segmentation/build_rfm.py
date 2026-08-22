"""Build a one-row-per-unique-customer RFM dataset from PostgreSQL."""

from __future__ import annotations

import pandas as pd

from src.analysis.data_loader import read_select

RFM_SQL = """
-- Grain: exactly one row per customer_unique_id.
WITH eligible_orders AS (
    SELECT o.order_id, o.customer_id, o.order_purchase_timestamp
    FROM orders o WHERE o.order_status NOT IN ('canceled', 'unavailable')
), order_payments AS (
    SELECT order_id, SUM(payment_value) AS order_value FROM payments GROUP BY order_id
), customer_activity AS (
    SELECT c.customer_unique_id,
           MIN(e.order_purchase_timestamp) AS first_purchase,
           MAX(e.order_purchase_timestamp) AS last_purchase,
           COUNT(DISTINCT e.order_id) AS frequency,
           SUM(COALESCE(op.order_value, 0)) AS monetary
    FROM eligible_orders e JOIN customers c ON c.customer_id = e.customer_id
    LEFT JOIN order_payments op ON op.order_id = e.order_id
    GROUP BY c.customer_unique_id
), latest_location AS (
    SELECT customer_unique_id, customer_state, customer_city
    FROM (
        SELECT c.customer_unique_id, c.customer_state, c.customer_city,
               ROW_NUMBER() OVER (PARTITION BY c.customer_unique_id ORDER BY e.order_purchase_timestamp DESC, e.order_id) AS rank
        FROM eligible_orders e JOIN customers c ON c.customer_id = e.customer_id
    ) ranked WHERE rank = 1
), reference AS (
    SELECT (MAX(order_purchase_timestamp)::date + 1) AS reference_date FROM eligible_orders
)
SELECT a.customer_unique_id, a.first_purchase, a.last_purchase,
       (r.reference_date - a.last_purchase::date)::int AS recency,
       a.frequency::int, a.monetary, l.customer_state, l.customer_city,
       r.reference_date
FROM customer_activity a JOIN latest_location l USING (customer_unique_id)
CROSS JOIN reference r
ORDER BY a.customer_unique_id
"""


def build_rfm_dataset() -> pd.DataFrame:
    """Load and validate the fixed-snapshot RFM customer dataset."""
    frame=read_select(RFM_SQL)
    frame["first_purchase"]=pd.to_datetime(frame["first_purchase"],errors="raise")
    frame["last_purchase"]=pd.to_datetime(frame["last_purchase"],errors="raise")
    frame["reference_date"]=pd.to_datetime(frame["reference_date"],errors="raise")
    if frame["customer_unique_id"].duplicated().any(): raise ValueError("RFM grain violation: duplicate customer_unique_id")
    if (frame[["recency","frequency","monetary"]]<0).any().any(): raise ValueError("RFM contains impossible negative values")
    return frame


if __name__ == "__main__":
    data=build_rfm_dataset(); print(data[["recency","frequency","monetary"]].describe().to_string()); print(f"Customers: {len(data):,}; revenue: R${data.monetary.sum():,.2f}; reference: {data.reference_date.iloc[0].date()}")
