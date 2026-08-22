WITH customer_orders AS (
    SELECT c.customer_unique_id, COUNT(*) AS orders
    FROM orders o JOIN customers c USING (customer_id)
    WHERE o.order_status NOT IN ('canceled', 'unavailable')
    GROUP BY c.customer_unique_id
)
SELECT COUNT(*) AS unique_customers, ROUND(AVG(orders), 3) AS average_orders_per_customer,
       COUNT(*) FILTER (WHERE orders = 1) AS one_time_customers,
       COUNT(*) FILTER (WHERE orders > 1) AS repeat_customers,
       ROUND(100.0 * COUNT(*) FILTER (WHERE orders > 1) / NULLIF(COUNT(*), 0), 2) AS repeat_customer_rate_pct
FROM customer_orders;

WITH order_payments AS (SELECT order_id, SUM(payment_value) order_value FROM payments GROUP BY order_id),
customer_value AS (
    SELECT c.customer_unique_id, COUNT(*) AS orders, SUM(op.order_value) AS total_spend,
           MAX(o.order_purchase_timestamp) AS last_order_at
    FROM orders o JOIN customers c USING (customer_id) JOIN order_payments op USING (order_id)
    WHERE o.order_status NOT IN ('canceled', 'unavailable') GROUP BY 1
)
SELECT customer_unique_id, orders, ROUND(total_spend, 2) AS total_spend, last_order_at
FROM customer_value ORDER BY total_spend DESC LIMIT 20;

WITH order_payments AS (SELECT order_id, SUM(payment_value) order_value FROM payments GROUP BY order_id),
customer_value AS (
    SELECT c.customer_unique_id, SUM(op.order_value) total_spend
    FROM orders o JOIN customers c USING (customer_id) JOIN order_payments op USING (order_id)
    WHERE o.order_status NOT IN ('canceled', 'unavailable') GROUP BY 1
)
SELECT ROUND(AVG(total_spend), 2) AS average_customer_spend,
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_spend)::numeric, 2) AS median_customer_spend
FROM customer_value;

SELECT c.customer_state, COUNT(DISTINCT c.customer_unique_id) AS unique_customers, COUNT(*) AS orders
FROM customers c JOIN orders o USING (customer_id)
WHERE o.order_status NOT IN ('canceled', 'unavailable') GROUP BY 1 ORDER BY orders DESC;

SELECT c.customer_city, c.customer_state, COUNT(DISTINCT c.customer_unique_id) AS unique_customers, COUNT(*) AS orders
FROM customers c JOIN orders o USING (customer_id)
WHERE o.order_status NOT IN ('canceled', 'unavailable') GROUP BY 1, 2 ORDER BY orders DESC LIMIT 25;

-- Base RFM features use the dataset's latest purchase as the reproducible snapshot date.
WITH order_payments AS (SELECT order_id, SUM(payment_value) order_value FROM payments GROUP BY order_id),
snapshot AS (SELECT MAX(order_purchase_timestamp)::date + 1 AS snapshot_date FROM orders),
rfm AS (
    SELECT c.customer_unique_id,
           (snapshot.snapshot_date - MAX(o.order_purchase_timestamp)::date) AS recency_days,
           COUNT(*) AS frequency, SUM(op.order_value) AS monetary
    FROM orders o JOIN customers c USING (customer_id) JOIN order_payments op USING (order_id) CROSS JOIN snapshot
    WHERE o.order_status NOT IN ('canceled', 'unavailable')
    GROUP BY c.customer_unique_id, snapshot.snapshot_date
)
SELECT ROUND(AVG(recency_days), 2) AS average_recency_days,
       ROUND(AVG(frequency), 3) AS average_frequency,
       ROUND(AVG(monetary), 2) AS average_monetary_value
FROM rfm;
