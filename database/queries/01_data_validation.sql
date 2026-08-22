-- Row counts for every imported table.
SELECT 'customers' AS table_name, COUNT(*) AS row_count FROM customers
UNION ALL SELECT 'products', COUNT(*) FROM products
UNION ALL SELECT 'sellers', COUNT(*) FROM sellers
UNION ALL SELECT 'product_category_translation', COUNT(*) FROM product_category_translation
UNION ALL SELECT 'geolocation', COUNT(*) FROM geolocation
UNION ALL SELECT 'orders', COUNT(*) FROM orders
UNION ALL SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL SELECT 'payments', COUNT(*) FROM payments
UNION ALL SELECT 'reviews', COUNT(*) FROM reviews
ORDER BY table_name;

SELECT COUNT(DISTINCT order_id) AS distinct_orders FROM orders;
SELECT COUNT(DISTINCT customer_id) AS distinct_customers FROM customers;
SELECT COUNT(DISTINCT customer_unique_id) AS distinct_unique_customers FROM customers;
SELECT COUNT(DISTINCT product_id) AS distinct_products FROM products;
SELECT COUNT(DISTINCT seller_id) AS distinct_sellers FROM sellers;

-- Duplicate primary/composite key candidates; every result should contain zero rows.
SELECT customer_id, COUNT(*) FROM customers GROUP BY customer_id HAVING COUNT(*) > 1;
SELECT order_id, COUNT(*) FROM orders GROUP BY order_id HAVING COUNT(*) > 1;
SELECT product_id, COUNT(*) FROM products GROUP BY product_id HAVING COUNT(*) > 1;
SELECT seller_id, COUNT(*) FROM sellers GROUP BY seller_id HAVING COUNT(*) > 1;
SELECT order_id, order_item_id, COUNT(*) FROM order_items GROUP BY order_id, order_item_id HAVING COUNT(*) > 1;
SELECT order_id, payment_sequential, COUNT(*) FROM payments GROUP BY order_id, payment_sequential HAVING COUNT(*) > 1;
SELECT review_id, order_id, COUNT(*) FROM reviews GROUP BY review_id, order_id HAVING COUNT(*) > 1;

-- NULL checks for important relationship columns.
SELECT
    (SELECT COUNT(*) FROM orders WHERE customer_id IS NULL) AS orders_customer_id_nulls,
    (SELECT COUNT(*) FROM order_items WHERE order_id IS NULL) AS items_order_id_nulls,
    (SELECT COUNT(*) FROM order_items WHERE product_id IS NULL) AS items_product_id_nulls,
    (SELECT COUNT(*) FROM order_items WHERE seller_id IS NULL) AS items_seller_id_nulls,
    (SELECT COUNT(*) FROM payments WHERE order_id IS NULL) AS payments_order_id_nulls,
    (SELECT COUNT(*) FROM reviews WHERE order_id IS NULL) AS reviews_order_id_nulls;

-- Orphan checks; all orphan counts should be zero.
SELECT COUNT(*) AS orders_without_customer FROM orders o LEFT JOIN customers c ON c.customer_id = o.customer_id WHERE c.customer_id IS NULL;
SELECT COUNT(*) AS items_without_order FROM order_items i LEFT JOIN orders o ON o.order_id = i.order_id WHERE o.order_id IS NULL;
SELECT COUNT(*) AS items_without_product FROM order_items i LEFT JOIN products p ON p.product_id = i.product_id WHERE p.product_id IS NULL;
SELECT COUNT(*) AS payments_without_order FROM payments p LEFT JOIN orders o ON o.order_id = p.order_id WHERE o.order_id IS NULL;
SELECT COUNT(*) AS reviews_without_order FROM reviews r LEFT JOIN orders o ON o.order_id = r.order_id WHERE o.order_id IS NULL;
