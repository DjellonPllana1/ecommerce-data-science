-- Each metric is calculated at its natural grain to prevent join fan-out.
WITH eligible_orders AS (
    SELECT o.* FROM orders o WHERE o.order_status NOT IN ('canceled', 'unavailable')
), order_payments AS (
    SELECT p.order_id, SUM(p.payment_value) AS order_value
    FROM payments p JOIN eligible_orders o USING (order_id) GROUP BY p.order_id
), customer_frequency AS (
    SELECT c.customer_unique_id, COUNT(*) AS orders
    FROM eligible_orders o JOIN customers c USING (customer_id) GROUP BY 1
), delivery AS (
    SELECT COUNT(*) AS delivered_orders,
           COUNT(*) FILTER (WHERE order_delivered_customer_date > order_estimated_delivery_date) AS late_orders
    FROM orders WHERE order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL
)
SELECT ROUND((SELECT SUM(order_value) FROM order_payments), 2) AS revenue,
       (SELECT COUNT(*) FROM eligible_orders) AS orders,
       (SELECT COUNT(*) FROM customer_frequency) AS unique_customers,
       ROUND((SELECT AVG(order_value) FROM order_payments), 2) AS average_order_value,
       ROUND(100.0 * (SELECT COUNT(*) FROM customer_frequency WHERE orders > 1) / NULLIF((SELECT COUNT(*) FROM customer_frequency), 0), 2) AS repeat_customer_rate_pct,
       ROUND((SELECT AVG(review_score) FROM reviews), 3) AS average_review_score,
       ROUND(100.0 * delivery.late_orders / NULLIF(delivery.delivered_orders, 0), 2) AS late_delivery_rate_pct
FROM delivery;
