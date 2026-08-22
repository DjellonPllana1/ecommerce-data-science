SELECT payment_type, COUNT(*) AS payment_records, COUNT(DISTINCT order_id) AS orders,
       ROUND(SUM(payment_value), 2) AS revenue,
       ROUND(AVG(payment_value), 2) AS average_payment_value
FROM payments GROUP BY 1 ORDER BY revenue DESC;

SELECT payment_installments, COUNT(*) AS payment_records,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS payment_percentage,
       ROUND(AVG(payment_value), 2) AS average_payment_value
FROM payments GROUP BY 1 ORDER BY 1;

SELECT CASE
         WHEN payment_installments <= 1 THEN '1'
         WHEN payment_installments <= 3 THEN '2-3'
         WHEN payment_installments <= 6 THEN '4-6'
         WHEN payment_installments <= 12 THEN '7-12'
         ELSE '13+'
       END AS installment_band,
       COUNT(*) AS payment_records, ROUND(AVG(payment_value), 2) AS average_payment_value,
       ROUND(SUM(payment_value), 2) AS revenue
FROM payments GROUP BY 1 ORDER BY MIN(payment_installments);

SELECT ROUND(AVG(payment_installments), 2) AS average_installments,
       ROUND(CORR(payment_value, payment_installments)::numeric, 3) AS payment_value_installment_correlation
FROM payments WHERE payment_type = 'credit_card';
