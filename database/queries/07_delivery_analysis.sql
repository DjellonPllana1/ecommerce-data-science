WITH delivered AS (
    SELECT o.order_id, c.customer_state, DATE_TRUNC('month', o.order_purchase_timestamp)::date AS purchase_month,
           EXTRACT(EPOCH FROM (o.order_delivered_customer_date - o.order_purchase_timestamp)) / 86400 AS delivery_days,
           EXTRACT(EPOCH FROM (o.order_estimated_delivery_date - o.order_purchase_timestamp)) / 86400 AS estimated_days,
           EXTRACT(EPOCH FROM (o.order_delivered_customer_date - o.order_estimated_delivery_date)) / 86400 AS delay_days
    FROM orders o JOIN customers c USING (customer_id)
    WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
)
SELECT ROUND(AVG(delivery_days)::numeric, 2) AS average_delivery_days,
       ROUND(AVG(estimated_days)::numeric, 2) AS average_estimated_days,
       COUNT(*) FILTER (WHERE delay_days < -1) AS early_deliveries,
       COUNT(*) FILTER (WHERE delay_days BETWEEN -1 AND 0) AS on_time_deliveries,
       COUNT(*) FILTER (WHERE delay_days > 0) AS late_deliveries,
       ROUND(100.0 * COUNT(*) FILTER (WHERE delay_days > 0) / NULLIF(COUNT(*), 0), 2) AS late_delivery_rate_pct,
       ROUND(AVG(delay_days) FILTER (WHERE delay_days > 0)::numeric, 2) AS average_late_delay_days
FROM delivered;

WITH delivered AS (
    SELECT c.customer_state,
           EXTRACT(EPOCH FROM (o.order_delivered_customer_date - o.order_purchase_timestamp)) / 86400 AS delivery_days,
           (o.order_delivered_customer_date > o.order_estimated_delivery_date) AS is_late
    FROM orders o JOIN customers c USING (customer_id)
    WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
)
SELECT customer_state, COUNT(*) AS delivered_orders, ROUND(AVG(delivery_days)::numeric, 2) AS average_delivery_days,
       ROUND(100.0 * COUNT(*) FILTER (WHERE is_late) / NULLIF(COUNT(*), 0), 2) AS late_delivery_rate_pct
FROM delivered GROUP BY 1 ORDER BY late_delivery_rate_pct DESC;

WITH delivered AS (
    SELECT DATE_TRUNC('month', order_purchase_timestamp)::date AS purchase_month,
           EXTRACT(EPOCH FROM (order_delivered_customer_date - order_purchase_timestamp)) / 86400 AS delivery_days,
           (order_delivered_customer_date > order_estimated_delivery_date) AS is_late
    FROM orders WHERE order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL
)
SELECT purchase_month, COUNT(*) AS delivered_orders, ROUND(AVG(delivery_days)::numeric, 2) AS average_delivery_days,
       ROUND(100.0 * COUNT(*) FILTER (WHERE is_late) / NULLIF(COUNT(*), 0), 2) AS late_delivery_rate_pct
FROM delivered GROUP BY 1 ORDER BY 1;

WITH order_freight AS (SELECT order_id, SUM(freight_value) freight_value FROM order_items GROUP BY order_id)
SELECT WIDTH_BUCKET(freight_value, 0, 200, 5) AS freight_bucket,
       ROUND(MIN(freight_value), 2) AS minimum_freight, ROUND(MAX(freight_value), 2) AS maximum_freight,
       COUNT(*) AS orders,
       ROUND(AVG(EXTRACT(EPOCH FROM (o.order_delivered_customer_date - o.order_purchase_timestamp)) / 86400)::numeric, 2) AS average_delivery_days
FROM orders o JOIN order_freight f USING (order_id)
WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
GROUP BY 1 ORDER BY 1;
