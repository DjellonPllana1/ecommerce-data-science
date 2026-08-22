SELECT ROUND(AVG(review_score), 3) AS average_review_score, COUNT(*) AS reviews FROM reviews;

SELECT review_score, COUNT(*) AS reviews,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS review_percentage
FROM reviews GROUP BY 1 ORDER BY 1;

SELECT CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN 'late' ELSE 'on_time_or_early' END AS delivery_status,
       COUNT(*) AS reviews, ROUND(AVG(r.review_score), 3) AS average_review_score
FROM reviews r JOIN orders o USING (order_id)
WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
GROUP BY 1 ORDER BY 1;

WITH order_reviews AS (SELECT order_id, AVG(review_score) review_score FROM reviews GROUP BY order_id)
SELECT COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') AS category,
       COUNT(*) AS reviewed_items, ROUND(AVG(r.review_score), 3) AS average_review_score
FROM order_items i JOIN products p USING (product_id) JOIN order_reviews r USING (order_id)
LEFT JOIN product_category_translation t USING (product_category_name)
GROUP BY 1 HAVING COUNT(*) >= 100 ORDER BY average_review_score DESC;

WITH order_reviews AS (SELECT order_id, AVG(review_score) review_score FROM reviews GROUP BY order_id)
SELECT i.seller_id, COUNT(*) AS reviewed_items, ROUND(AVG(r.review_score), 3) AS average_review_score
FROM order_items i JOIN order_reviews r USING (order_id)
GROUP BY 1 HAVING COUNT(*) >= 100 ORDER BY average_review_score DESC LIMIT 25;

SELECT CASE
         WHEN o.order_delivered_customer_date <= o.order_estimated_delivery_date THEN 'on_time_or_early'
         WHEN o.order_delivered_customer_date <= o.order_estimated_delivery_date + INTERVAL '3 days' THEN '1_to_3_days_late'
         WHEN o.order_delivered_customer_date <= o.order_estimated_delivery_date + INTERVAL '7 days' THEN '4_to_7_days_late'
         ELSE 'more_than_7_days_late'
       END AS delay_band, COUNT(*) AS reviews, ROUND(AVG(r.review_score), 3) AS average_review_score
FROM reviews r JOIN orders o USING (order_id)
WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
GROUP BY 1 ORDER BY MIN(o.order_delivered_customer_date - o.order_estimated_delivery_date);
