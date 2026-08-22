WITH seller_metrics AS (
    SELECT s.seller_id, s.seller_state, SUM(i.price) AS item_revenue,
           COUNT(DISTINCT i.order_id) AS orders, COUNT(*) AS items_sold, AVG(i.price) AS average_item_value
    FROM order_items i JOIN orders o USING (order_id) JOIN sellers s USING (seller_id)
    WHERE o.order_status NOT IN ('canceled', 'unavailable') GROUP BY 1, 2
)
SELECT seller_id, seller_state, ROUND(item_revenue, 2) AS item_revenue,
       orders, items_sold, ROUND(average_item_value, 2) AS average_item_value
FROM seller_metrics ORDER BY item_revenue DESC LIMIT 25;

SELECT seller_state, COUNT(*) AS sellers FROM sellers GROUP BY 1 ORDER BY sellers DESC;

WITH seller_revenue AS (
    SELECT i.seller_id, SUM(i.price) AS revenue
    FROM order_items i JOIN orders o USING (order_id)
    WHERE o.order_status NOT IN ('canceled', 'unavailable') GROUP BY 1
), ranked AS (
    SELECT *, ROW_NUMBER() OVER (ORDER BY revenue DESC) AS revenue_rank, SUM(revenue) OVER () AS total_revenue
    FROM seller_revenue
)
SELECT ROUND(100 * SUM(revenue) FILTER (WHERE revenue_rank <= 10) / NULLIF(MAX(total_revenue), 0), 2) AS top_10_revenue_pct,
       ROUND(100 * SUM(revenue) FILTER (WHERE revenue_rank <= 100) / NULLIF(MAX(total_revenue), 0), 2) AS top_100_revenue_pct,
       ROUND(100 * SUM(revenue) FILTER (WHERE revenue_rank <= CEIL((SELECT COUNT(*) FROM ranked) * 0.01)) / NULLIF(MAX(total_revenue), 0), 2) AS top_1_percent_revenue_pct
FROM ranked;
