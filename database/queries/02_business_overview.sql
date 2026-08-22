-- Payments are aggregated at order grain before calculating order-value metrics.
WITH order_payments AS (
    SELECT order_id, SUM(payment_value) AS order_value,
           SUM(payment_installments * payment_value) / NULLIF(SUM(payment_value), 0) AS weighted_installments
    FROM payments GROUP BY order_id
), core AS (
    SELECT COUNT(*) FILTER (WHERE order_status NOT IN ('canceled', 'unavailable')) AS total_orders,
           COUNT(DISTINCT c.customer_unique_id) FILTER (WHERE order_status NOT IN ('canceled', 'unavailable')) AS unique_customers
    FROM orders o JOIN customers c ON c.customer_id = o.customer_id
)
SELECT core.total_orders, core.unique_customers,
       (SELECT COUNT(*) FROM products) AS total_products,
       (SELECT COUNT(*) FROM sellers) AS total_sellers,
       ROUND(SUM(op.order_value), 2) AS total_revenue,
       ROUND(AVG(op.order_value), 2) AS average_order_value,
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY op.order_value)::numeric, 2) AS median_order_value,
       ROUND(AVG(op.weighted_installments), 2) AS average_payment_installments
FROM core CROSS JOIN orders o JOIN order_payments op ON op.order_id = o.order_id
WHERE o.order_status NOT IN ('canceled', 'unavailable')
GROUP BY core.total_orders, core.unique_customers;

SELECT order_status, COUNT(*) AS order_count,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS percentage_of_orders
FROM orders GROUP BY order_status ORDER BY order_count DESC;
