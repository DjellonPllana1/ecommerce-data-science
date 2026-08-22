from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class HealthResponse(BaseModel):
    api_status: str
    database_connected: bool
    late_delivery_model_available: bool
    segmentation_model_available: bool
    orders_forecast_model_available: bool
    revenue_forecast_model_available: bool

class OverviewResponse(BaseModel):
    total_eligible_orders: int
    total_revenue: float
    average_order_value: float
    unique_customers: int
    repeat_customer_rate: float
    average_delivery_duration_days: float | None
    late_delivery_rate: float | None

class MonthlySales(BaseModel):
    month: date
    orders: int
    revenue: float
    average_order_value: float

class CategoryMetric(BaseModel):
    category: str
    items_sold: int
    item_revenue: float

class DeliveryMetric(BaseModel):
    month: date
    delivered_orders: int
    average_delivery_days: float
    late_delivery_rate: float

class CustomerSummary(BaseModel):
    customer_type: str
    customers: int
    customer_share: float
    revenue: float
    revenue_share: float

class LateDeliveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    purchase_month: int = Field(ge=1, le=12)
    purchase_day_of_week: int = Field(ge=0, le=6)
    purchase_hour: int = Field(ge=0, le=23)
    customer_zip_region: int = Field(ge=0)
    item_value: float = Field(ge=0)
    freight_value: float = Field(ge=0)
    item_count: int = Field(ge=1)
    unique_products: int = Field(ge=1)
    seller_count: int = Field(ge=1)
    total_product_weight_g: float = Field(ge=0)
    average_product_length_cm: float = Field(ge=0)
    average_product_height_cm: float = Field(ge=0)
    average_product_width_cm: float = Field(ge=0)
    payment_value: float = Field(ge=0)
    payment_installments: int = Field(ge=0)
    estimated_delivery_window_days: float = Field(gt=0)
    customer_state: str = Field(min_length=2, max_length=2)
    dominant_product_category: str = Field(min_length=1)
    dominant_seller_state: str = Field(min_length=2, max_length=2)
    same_customer_seller_state: int = Field(ge=0, le=1)
    payment_type: str = Field(min_length=1)

class LateDeliveryResponse(BaseModel):
    late_delivery_probability: float = Field(ge=0, le=1)
    predicted_class: int
    risk_level: Literal["low", "medium", "high"]
    interpretation: str

class SegmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recency: float = Field(ge=0)
    frequency: float = Field(ge=0)
    monetary: float = Field(ge=0)

class SegmentResponse(BaseModel):
    cluster_id: int
    cluster_name: str

class ForecastDay(BaseModel):
    date: date
    predicted_orders: float
    predicted_revenue: float
    orders_lower_bound: float
    orders_upper_bound: float
    revenue_lower_bound: float
    revenue_upper_bound: float

class ForecastResponse(BaseModel):
    horizon: int
    interval_type: str
    forecasts: list[ForecastDay]
