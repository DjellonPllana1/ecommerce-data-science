-- Revenue uses one payment total per order and excludes canceled/unavailable orders.
WITH order_payments AS (
    SELECT order_id, SUM(payment_value) AS order_value FROM payments GROUP BY order_id
), monthly AS (
    SELECT DATE_TRUNC('month', o.order_purchase_timestamp)::date AS month,
           COUNT(*) AS orders, SUM(op.order_value) AS revenue,
           AVG(op.order_value) AS average_order_value
    FROM orders o JOIN order_payments op USING (order_id)
    WHERE o.order_status NOT IN ('canceled', 'unavailable')
    GROUP BY 1
)
SELECT current.month, current.orders, ROUND(current.revenue, 2) AS revenue,
       ROUND(current.average_order_value, 2) AS average_order_value,
       CASE WHEN current.orders >= 100 AND prior_month.orders >= 100
            THEN ROUND(100 * (current.revenue - prior_month.revenue) / NULLIF(prior_month.revenue, 0), 2)
       END AS mom_revenue_growth_pct,
       CASE WHEN current.orders >= 100 AND prior_year.orders >= 100
            THEN ROUND(100 * (current.revenue - prior_year.revenue) / NULLIF(prior_year.revenue, 0), 2)
       END AS yoy_revenue_growth_pct
FROM monthly current
LEFT JOIN monthly prior_month ON prior_month.month = (current.month - INTERVAL '1 month')::date
LEFT JOIN monthly prior_year ON prior_year.month = (current.month - INTERVAL '1 year')::date
ORDER BY current.month;

WITH order_payments AS (SELECT order_id, SUM(payment_value) order_value FROM payments GROUP BY order_id)
SELECT DATE_TRUNC('month', order_purchase_timestamp)::date AS month,
       ROUND(SUM(order_value), 2) AS revenue, COUNT(*) AS orders
FROM orders JOIN order_payments USING (order_id)
WHERE order_status NOT IN ('canceled', 'unavailable')
GROUP BY 1 ORDER BY revenue DESC LIMIT 10;

WITH order_payments AS (SELECT order_id, SUM(payment_value) order_value FROM payments GROUP BY order_id)
SELECT EXTRACT(ISODOW FROM order_purchase_timestamp)::int AS iso_day_of_week,
       TO_CHAR(order_purchase_timestamp, 'FMDay') AS day_name,
       COUNT(*) AS orders, ROUND(SUM(order_value), 2) AS revenue,
       ROUND(AVG(order_value), 2) AS average_order_value
FROM orders JOIN order_payments USING (order_id)
WHERE order_status NOT IN ('canceled', 'unavailable')
GROUP BY 1, 2 ORDER BY 1;
