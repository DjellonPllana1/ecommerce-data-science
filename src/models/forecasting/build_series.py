"""Construct continuous daily forecasting series from PostgreSQL."""
from __future__ import annotations
import pandas as pd
from src.analysis.data_loader import read_select
from .config import MODEL_END,MODEL_START

DAILY_SQL="""
WITH eligible AS (
 SELECT order_id, order_purchase_timestamp::date AS purchase_date FROM orders
 WHERE order_status NOT IN ('canceled','unavailable')
), order_payments AS (SELECT order_id,SUM(payment_value) order_value FROM payments GROUP BY order_id)
SELECT e.purchase_date,COUNT(DISTINCT e.order_id) AS daily_orders,SUM(COALESCE(p.order_value,0)) AS daily_revenue
FROM eligible e LEFT JOIN order_payments p ON p.order_id=e.order_id GROUP BY e.purchase_date ORDER BY e.purchase_date
"""
def build_daily_series()->tuple[pd.DataFrame,pd.DataFrame]:
    observed=read_select(DAILY_SQL); observed["date"]=pd.to_datetime(observed.pop("purchase_date")); index=pd.date_range(observed.date.min(),observed.date.max(),freq="D")
    full=observed.set_index("date").reindex(index,fill_value=0).rename_axis("date").reset_index(); full["daily_orders"]=full.daily_orders.astype(int)
    if full.date.duplicated().any() or not full.date.is_monotonic_increasing: raise ValueError("Daily series date validation failed")
    if abs(full.daily_revenue.sum()-15739137.01)>.01: raise ValueError("Revenue reconciliation failed")
    modeling=full.set_index("date").loc[MODEL_START:MODEL_END].copy()
    return full,modeling
