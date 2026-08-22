from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from src.ingestion.load_data import get_engine
from api.schemas import OverviewResponse, MonthlySales, CategoryMetric, DeliveryMetric, CustomerSummary

router = APIRouter(prefix="/analytics", tags=["analytics"])

def query(sql):
    engine=get_engine()
    try:
        with engine.connect() as c:
            c.execute(text("SET TRANSACTION READ ONLY")); return [dict(r._mapping) for r in c.execute(text(sql))]
    except Exception as exc: raise HTTPException(503, f"Analytics database unavailable: {exc}") from exc
    finally: engine.dispose()

OVERVIEW="""WITH eo AS (SELECT * FROM orders WHERE order_status NOT IN ('canceled','unavailable')), op AS (SELECT p.order_id,SUM(p.payment_value) value FROM payments p JOIN eo USING(order_id) GROUP BY 1), cf AS (SELECT c.customer_unique_id,COUNT(*) n,SUM(COALESCE(op.value,0)) revenue FROM eo JOIN customers c USING(customer_id) LEFT JOIN op USING(order_id) GROUP BY 1), d AS (SELECT EXTRACT(EPOCH FROM (order_delivered_customer_date-order_purchase_timestamp))/86400 days, order_delivered_customer_date>order_estimated_delivery_date late FROM orders WHERE order_status='delivered' AND order_delivered_customer_date IS NOT NULL) SELECT (SELECT COUNT(*) FROM eo) total_eligible_orders,(SELECT COALESCE(SUM(value),0) FROM op) total_revenue,(SELECT COALESCE(AVG(value),0) FROM op) average_order_value,(SELECT COUNT(*) FROM cf) unique_customers,100.0*(SELECT COUNT(*) FROM cf WHERE n>1)/NULLIF((SELECT COUNT(*) FROM cf),0) repeat_customer_rate,(SELECT AVG(days) FROM d) average_delivery_duration_days,100.0*(SELECT COUNT(*) FROM d WHERE late)/NULLIF((SELECT COUNT(*) FROM d),0) late_delivery_rate"""
MONTHLY="""WITH eo AS (SELECT * FROM orders WHERE order_status NOT IN ('canceled','unavailable')),op AS(SELECT order_id,SUM(payment_value) value FROM payments GROUP BY 1) SELECT DATE_TRUNC('month',o.order_purchase_timestamp)::date AS month,COUNT(*) AS orders,COALESCE(SUM(op.value),0) AS revenue,COALESCE(AVG(op.value),0) AS average_order_value FROM eo o LEFT JOIN op USING(order_id) GROUP BY 1 ORDER BY 1"""
CATEGORIES="""SELECT COALESCE(t.product_category_name_english,p.product_category_name,'unknown') category,COUNT(*) items_sold,SUM(i.price) item_revenue FROM order_items i JOIN orders o USING(order_id) JOIN products p USING(product_id) LEFT JOIN product_category_translation t USING(product_category_name) WHERE o.order_status NOT IN ('canceled','unavailable') GROUP BY 1 ORDER BY item_revenue DESC LIMIT 20"""
DELIVERY="""SELECT DATE_TRUNC('month',order_purchase_timestamp)::date AS month,COUNT(*) AS delivered_orders,AVG(EXTRACT(EPOCH FROM(order_delivered_customer_date-order_purchase_timestamp))/86400) AS average_delivery_days,100.0*COUNT(*) FILTER(WHERE order_delivered_customer_date>order_estimated_delivery_date)/COUNT(*) AS late_delivery_rate FROM orders WHERE order_status='delivered' AND order_delivered_customer_date IS NOT NULL GROUP BY 1 ORDER BY 1"""
CUSTOMERS="""WITH eo AS(SELECT * FROM orders WHERE order_status NOT IN('canceled','unavailable')),op AS(SELECT order_id,SUM(payment_value) value FROM payments GROUP BY 1),cf AS(SELECT c.customer_unique_id,COUNT(*) n,SUM(COALESCE(op.value,0)) revenue FROM eo JOIN customers c USING(customer_id) LEFT JOIN op USING(order_id) GROUP BY 1),s AS(SELECT CASE WHEN n>1 THEN 'Repeat' ELSE 'One-time' END customer_type,COUNT(*) customers,SUM(revenue) revenue FROM cf GROUP BY 1) SELECT customer_type,customers,100.0*customers/SUM(customers)OVER() customer_share,revenue,100.0*revenue/SUM(revenue)OVER() revenue_share FROM s ORDER BY customers DESC"""

@router.get('/overview',response_model=OverviewResponse)
def overview(): return query(OVERVIEW)[0]
@router.get('/monthly-sales',response_model=list[MonthlySales])
def monthly_sales(): return query(MONTHLY)
@router.get('/categories',response_model=list[CategoryMetric])
def categories(): return query(CATEGORIES)
@router.get('/delivery',response_model=list[DeliveryMetric])
def delivery(): return query(DELIVERY)
@router.get('/customer-summary',response_model=list[CustomerSummary])
def customer_summary(): return query(CUSTOMERS)
