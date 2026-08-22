# Interview Guide

## 60-second project explanation

I built an end-to-end e-commerce intelligence platform on Olist: PostgreSQL and grain-safe SQL, reproducible EDA, leakage-safe late-delivery classification, fixed-snapshot RFM/KMeans segmentation, and daily forecasting with expanding-window validation. Persisted scikit-learn pipelines are served through FastAPI and explored in a seven-view Streamlit dashboard, with three services packaged in Docker Compose. I report trade-offs directly, including modest delivery precision and increasing forecast error by horizon.

## 5-minute technical explanation

Explain relational grain first, then the 98,207-order EDA. Cover chronological classifier selection and prohibited post-outcome fields; fixed-snapshot log1p/scaled RFM; and expanding forecast folds against weekly seasonal baselines. Finish with cached artifacts, Pydantic validation, read-only SQL, Streamlit communication, and limitations.

## Why PostgreSQL was used

Olist is naturally relational. PostgreSQL enforces keys/types, makes grain explicit, supports reusable SQL, and creates a realistic storage/service boundary.

## How SQL joins avoided revenue fan-out

Payments and items are both one-to-many from orders. Payments are aggregated per order before order joins; category GMV uses item prices and never repeats full order payment per item.

## How data leakage was prevented

Only purchase-time/pre-dispatch fields are accepted. Actual carrier/delivery timestamps, delays, reviews, targets, and IDs are prohibited. Model/threshold selection uses train/validation periods; the chronological test is untouched.

## Why chronological validation was required for forecasting

Random splitting leaks future demand patterns. Expanding windows preserve order, emulate repeated forecasting, and leave a final 30-day holdout.

## Why KMeans selected k=2

k=2 silhouette was 0.708 versus 0.399 at k=3 and met cluster-size rules. It honestly reflects dominant one-time purchasing rather than forcing decorative personas.

## Why rule-based RFM remained useful

KMeans found two broad groups; transparent rules retain lifecycle states such as promising, at-risk, and hibernating for action planning.

## Why forecasting baselines matter

Learned models must beat simple deployable alternatives. Weekly seasonality made SeasonalNaive7 the key benchmark; winners improved MAE 7.76% for orders and 4.75% for revenue.

## Model limitations

Delivery events are imbalanced and precision is low; current carrier signals are absent. RFM depends on the window. Forecasts lack promotions/holidays and compound recursive error.

## What would change in a real production system

Add orchestration, registry, CI/CD, secret management, authentication, observability, drift/calibration monitoring, prediction logging, retraining evaluation, canaries, and intervention experiments.
