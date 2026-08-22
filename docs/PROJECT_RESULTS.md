# Validated Project Results

All values come from persisted metadata and generated reports.

## Dataset and EDA

- 99,441 orders; 112,650 items; 103,886 payments; 99,224 reviews.
- 98,207 eligible orders; 94,990 unique customers; R$15,739,137.01 revenue; R$160.27 AOV.
- Purchases span 2016-09-04 to 2018-09-03; repeat rate is 3.04%.
- November 2017: 7,423 orders and R$1,172,639.23 revenue.
- Delivery averages 12.56 days; late rate is 8.11%.
- Late reviews average 2.566 (n=7,700) versus 4.294 on time/early (n=88,653).
- Delivery delay vs review: Pearson -0.267, Spearman -0.176, n=96,353.

## Late-delivery model

Logistic Regression won by validation PR-AUC. Threshold 0.55 was selected on validation using F2; the chronological test remained untouched.

| PR-AUC | ROC-AUC | Precision | Recall | F1 | Balanced accuracy |
|---:|---:|---:|---:|---:|---:|
| 0.1132 | 0.6574 | 0.0996 | 0.6646 | 0.1733 | 0.6196 |

Confusion matrix: TN 7,766; FP 5,748; FN 321; TP 636. All 21 features passed the prediction-time leakage audit.

## RFM and KMeans

Reference date: 2018-09-04. RFM revenue reconciles to R$15,739,137.01. k=2 achieved silhouette 0.7081. One-Time Customers: 92,102 (96.96%, 94.34% of revenue); Repeat High-Value Customers: 2,888 (3.04%, 5.66% of revenue).

## Forecast backtesting

The full continuous series has 730 days; modeling uses 598 days and three expanding 30-day folds.

| Target | Winner MAE | SeasonalNaive7 MAE | Improvement |
|---|---:|---:|---:|
| Orders — Random Forest | 40.70 | 44.12 | 7.76% |
| Revenue — Histogram Gradient Boosting | R$8,024.51 | R$8,424.68 | 4.75% |

## Forecast holdout

| Target | Horizon | MAE | RMSE | MAPE |
|---|---:|---:|---:|---:|
| Orders | 7 | 12.18 | 16.63 | 5.91% |
| Orders | 14 | 37.33 | 49.41 | 13.68% |
| Orders | 30 | 43.03 | 55.70 | 14.88% |
| Revenue | 7 | R$4,087.51 | R$4,661.66 | 10.65% |
| Revenue | 14 | R$7,453.31 | R$8,826.35 | 17.05% |
| Revenue | 30 | R$7,720.60 | R$9,349.15 | 17.14% |

## Known limitations

The period is short and historical. Promotions, operational capacity, traffic, holidays, weather, campaigns, margins, and macroeconomics are absent. Classifier precision is modest; clusters are descriptive; recursive uncertainty grows with horizon; planning bands are empirical.
