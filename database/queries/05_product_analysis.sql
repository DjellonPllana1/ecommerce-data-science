-- Item price is used as category/product GMV; payments are not joined to items to avoid fan-out.
WITH category_sales AS (
    SELECT COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') AS category,
           SUM(i.price) AS item_revenue, COUNT(*) AS items_sold,
           AVG(i.price) AS average_product_price, COUNT(DISTINCT p.product_id) AS unique_products,
           AVG(i.freight_value) AS average_freight_cost
    FROM order_items i JOIN orders o USING (order_id) JOIN products p USING (product_id)
    LEFT JOIN product_category_translation t USING (product_category_name)
    WHERE o.order_status NOT IN ('canceled', 'unavailable') GROUP BY 1
)
SELECT category, ROUND(item_revenue, 2) AS item_revenue, items_sold,
       ROUND(average_product_price, 2) AS average_product_price,
       unique_products, ROUND(average_freight_cost, 2) AS average_freight_cost
FROM category_sales ORDER BY item_revenue DESC;

SELECT i.product_id, COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') AS category,
       ROUND(SUM(i.price), 2) AS item_revenue, COUNT(*) AS items_sold
FROM order_items i JOIN orders o USING (order_id) JOIN products p USING (product_id)
LEFT JOIN product_category_translation t USING (product_category_name)
WHERE o.order_status NOT IN ('canceled', 'unavailable')
GROUP BY 1, 2 ORDER BY item_revenue DESC LIMIT 20;

WITH order_reviews AS (SELECT order_id, AVG(review_score) review_score FROM reviews GROUP BY order_id),
category_reviews AS (
    SELECT COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') AS category,
           AVG(r.review_score) AS average_review_score, COUNT(*) AS reviewed_items
    FROM order_items i JOIN products p USING (product_id) JOIN order_reviews r USING (order_id)
    LEFT JOIN product_category_translation t USING (product_category_name) GROUP BY 1
)
SELECT category, ROUND(average_review_score, 3) AS average_review_score, reviewed_items
FROM category_reviews WHERE reviewed_items >= 100 ORDER BY average_review_score DESC;
