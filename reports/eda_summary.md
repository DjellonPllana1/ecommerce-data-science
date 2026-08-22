# Olist Exploratory Data Analysis Summary

## Executive summary

The PostgreSQL-backed EDA covers 98,207 eligible orders and 94,990 unique customers. Eligible payment revenue is R$15,739,137.01; canceled and unavailable orders are excluded from commercial metrics.

## Dataset overview

| Dataset | Rows | Columns | Duplicate business keys | Missing cells |
|---|---:|---:|---:|---:|
| orders | 99,441 | 22 | 0 | 13,805 |
| items | 112,650 | 9 | 0 | 1,603 |
| reviews | 99,224 | 7 | 0 | 5,742 |
| customers | 94,990 | 9 | 0 | 0 |

## Data-quality findings

- 610 products lack a category.
- 2 payment records report zero installments and 3 use an undefined payment method.
- 8 delivered orders lack an actual delivery timestamp.
- Negative item prices: 0; negative freight values: 0; negative actual delivery durations: 0.
- Purchases range from 2016-09-04 21:15:19 to 2018-09-03 09:06:57; sparse boundary months are excluded from strongest-month comparisons.
- Outliers are retained; distribution plots are visually capped at the 99th percentile and labeled accordingly.

## Customer and sales findings

- Repeat customer rate: 3.04%.
- Strongest complete month: 2017-11 with 7,423 orders and R$1,172,639.23 revenue.
- Average order value: R$160.27.

## Product findings

- The highest item-revenue category is `health_beauty` at R$1,255,695.13. Item price is treated as category GMV so payments are not duplicated across items.

## Delivery and customer satisfaction

- Average delivery duration is 12.56 days and the late-delivery rate is 8.11%.
- Late deliveries average 2.566 stars (median 2.0, n=7,700); on-time/early deliveries average 4.294 (median 5.0, n=88,653).

## Statistical relationships

- Delivery delay vs review score: Pearson -0.267, Spearman -0.176, n=96,353.
- Freight value vs delivery duration: Pearson 0.167, Spearman 0.382, n=96,470.
- Order value vs freight value has Pearson correlation 0.492; order value vs maximum installments has Spearman correlation 0.382.
- Major-state mean delivery duration: SP 8.76 days, MG 12.01, and RJ 15.31.
- These are associations, not causal estimates.

## Potential ML problems

1. **Late-delivery prediction** — target: late/not late per order; pre-dispatch product, seller, geography, freight and timing features; exclude actual delivery timestamps to prevent leakage. The target is observed for delivered orders and has direct operational value.
2. **Review-score prediction** — target: ordinal review score per reviewed order; use pre-delivery order context and planned logistics, while excluding review text and actual post-outcome timing when predicting early.
3. **Repeat-purchase prediction** — target: another purchase within a fixed future window per customer snapshot; historical RFM features are useful, but temporal splitting is mandatory and the low positive rate requires careful evaluation.
4. **RFM segmentation** — unit: customer; features: recency, frequency, monetary value at a fixed snapshot. This is unsupervised and must avoid using activity after the snapshot.
5. **Sales forecasting** — target: future daily/weekly order volume or revenue; partial boundary periods, promotions unavailable in Olist, and a short history limit reliability.

## Artifacts

Generated 24 figures in `reports/figures/` and machine-readable metrics in `reports/data/eda_metrics.csv`.
