# Five-Minute Demo Guide

## 0:00–0:35 — Executive Overview

Say: “This is live PostgreSQL and persisted inference, not screenshots.” Show R$15.74M revenue, 98,207 eligible orders, 94,990 customers, 3.04% repeat rate, and 8.11% late rate.

## 0:35–1:10 — Business story

Show monthly trends. Explain that retention is the main commercial weakness, delivery reliability the operational risk, and forecasts support capacity planning.

## 1:10–1:50 — Customer Intelligence

Show cluster shares. Enter Recency 120, Frequency 2, Monetary 250. Explain that persisted preprocessing and KMeans run without retraining, while rule-based RFM adds lifecycle detail.

## 1:50–2:40 — Delivery Risk

Run the default form. Explain that only 21 pre-dispatch features are accepted. The result is probabilistic: 66.5% test recall but modest precision, so it prioritizes review rather than automating action.

## 2:40–3:25 — Sales Forecasting

Select seven days. Show orders, revenue, and planning interval. Explain expanding-window backtests, weekly baselines, and rising long-horizon error.

## 3:25–4:15 — Model Performance

Show the confusion matrix, k-selection evidence, and forecast comparison. Emphasize untouched test/holdout data and baseline discipline.

## 4:15–4:50 — Swagger

Open `/docs` and expand a prediction route. Mention Pydantic validation, read-only SQL, and cached artifacts.

## 4:50–5:00 — Close

Say: “This demonstrates relational analytics, responsible validation, reusable inference, API design, and business communication. Next steps are monitoring, CI/CD, authentication, and richer operational data.”
