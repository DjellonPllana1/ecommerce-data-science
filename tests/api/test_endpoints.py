from fastapi.testclient import TestClient
from api.dependencies import model_bundle
from api.main import app

client=TestClient(app)
DELIVERY={"purchase_month":6,"purchase_day_of_week":2,"purchase_hour":14,"customer_zip_region":1300,"item_value":150,"freight_value":20,"item_count":1,"unique_products":1,"seller_count":1,"total_product_weight_g":1200,"average_product_length_cm":30,"average_product_height_cm":15,"average_product_width_cm":20,"payment_value":170,"payment_installments":2,"estimated_delivery_window_days":20,"customer_state":"SP","dominant_product_category":"bed_bath_table","dominant_seller_state":"SP","same_customer_seller_state":1,"payment_type":"credit_card"}

def test_health():
    body=client.get('/health').json(); assert body['api_status']=='ok'; assert body['database_connected']; assert all(body[key] for key in body if key.endswith('_available'))
def test_overview():
    response=client.get('/analytics/overview'); assert response.status_code==200; assert response.json()['total_eligible_orders']>0
def test_analytics_collections():
    for path in ('/analytics/monthly-sales','/analytics/categories','/analytics/delivery','/analytics/customer-summary'):
        response=client.get(path); assert response.status_code==200; assert len(response.json())>0
def test_valid_delivery_prediction():
    response=client.post('/predict/late-delivery',json=DELIVERY); assert response.status_code==200; assert 0<=response.json()['late_delivery_probability']<=1
def test_invalid_delivery_input():
    response=client.post('/predict/late-delivery',json={**DELIVERY,'purchase_month':13}); assert response.status_code==422
    leakage=client.post('/predict/late-delivery',json={**DELIVERY,'review_score':1}); assert leakage.status_code==422
def test_customer_segment():
    response=client.post('/predict/customer-segment',json={'recency':120,'frequency':2,'monetary':250}); assert response.status_code==200; assert 'cluster_name' in response.json()
def test_forecast_supported_horizons():
    for horizon in (7,14,30):
        response=client.get('/forecast',params={'horizon':horizon}); assert response.status_code==200; assert len(response.json()['forecasts'])==horizon
def test_invalid_forecast_horizon(): assert client.get('/forecast',params={'horizon':8}).status_code==422
def test_artifacts_are_cached_not_retrained(): assert model_bundle() is model_bundle()
