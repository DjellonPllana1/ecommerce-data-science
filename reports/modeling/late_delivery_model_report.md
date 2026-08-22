# Late Delivery Prediction Model Report

## Business problem

Predict late-delivery risk at purchase time so operations teams can prioritize preventive action. Late deliveries are rare and costly, so PR-AUC, recall, precision, and F1 are more informative than plain accuracy.

## Dataset and target

The PostgreSQL dataset contains 96,470 delivered orders at exactly one row per order. The target is 1 when actual customer delivery is later than the estimated delivery timestamp. There are 7,826 late orders (8.11%). Item, payment, product, and seller inputs are aggregated before joining.

## Leakage policy and features

The 21 selected features are purchase-time calendar, location, basket, catalog, seller, checkout payment, and estimated-window attributes. Actual delivery/carrier timestamps, delivery duration/delay, reviews, target, and raw IDs are excluded. `feature_audit.csv` records prediction-time availability for every feature.

## Temporal split

| Split | Rows | Start | End | Late prevalence |
|---|---:|---|---|---:|
| train | 67,529 | 2016-09-15 12:16:38 | 2018-04-15 20:12:35 | 9.03% |
| validation | 14,470 | 2018-04-15 20:17:11 | 2018-06-21 08:29:29 | 5.34% |
| test | 14,471 | 2018-06-21 08:41:07 | 2018-08-29 15:00:37 | 6.61% |

The final test period remained untouched during model choice and validation-only threshold optimization.

## Models and validation

| Model | Split | PR-AUC | ROC-AUC | Precision | Recall | F1 |
|---|---|---:|---:|---:|---:|---:|
| DummyClassifier | train | 0.0903 | 0.5000 | 0.0000 | 0.0000 | 0.0000 |
| DummyClassifier | validation | 0.0534 | 0.5000 | 0.0000 | 0.0000 | 0.0000 |
| LogisticRegression | train | 0.2153 | 0.7128 | 0.1622 | 0.6403 | 0.2588 |
| LogisticRegression | validation | 0.1580 | 0.7678 | 0.1141 | 0.7167 | 0.1969 |
| RandomForestClassifier | train | 0.4942 | 0.9030 | 0.3454 | 0.7434 | 0.4717 |
| RandomForestClassifier | validation | 0.1405 | 0.7215 | 0.1758 | 0.2031 | 0.1885 |
| HistGradientBoostingClassifier | train | 0.3541 | 0.8377 | 0.2390 | 0.7515 | 0.3627 |
| HistGradientBoostingClassifier | validation | 0.1276 | 0.7115 | 0.1488 | 0.2794 | 0.1942 |

The winning model is **LogisticRegression**, selected by validation PR-AUC rather than accuracy or test performance.

## Threshold and final test

Validation F2 optimization selected threshold **0.55**, placing extra weight on identifying late orders. On the untouched test set: PR-AUC 0.1132, ROC-AUC 0.6574, precision 0.0996, recall 0.6646, F1 0.1733, and balanced accuracy 0.6196. Confusion matrix: TN=7,766, FP=5,748, FN=321, TP=636.

## Predictive importance

Permutation importance measures validation PR-AUC change and indicates association, not causation.

| Feature | Mean importance | Std. deviation |
|---|---:|---:|
| estimated_delivery_window_days | 0.075397 | 0.002364 |
| customer_state | 0.055225 | 0.006603 |
| same_customer_seller_state | 0.046155 | 0.004014 |
| customer_zip_region | 0.042588 | 0.002237 |
| dominant_seller_state | 0.015778 | 0.002520 |
| payment_value | 0.004994 | 0.000695 |
| item_count | 0.002553 | 0.000884 |
| seller_count | 0.002005 | 0.000988 |
| freight_value | 0.001765 | 0.001421 |
| average_product_width_cm | 0.001757 | 0.000433 |
| purchase_month | 0.000877 | 0.000065 |
| purchase_hour | 0.000580 | 0.000047 |
| unique_products | 0.000159 | 0.000236 |
| payment_installments | 0.000072 | 0.000398 |
| purchase_day_of_week | -0.000006 | 0.000079 |

## Error analysis

False negatives are genuinely late orders the model did not flag. Detailed state, value-band, category, month, and example error tables are saved under `reports/modeling/`. Segment results with small samples should not drive policy without uncertainty analysis.

## Limitations and production improvements

- Olist covers a historical marketplace period and may not represent current logistics.
- The database lacks live carrier capacity, weather, traffic, holidays, and seller operational load.
- Estimated delivery windows can encode existing platform logistics knowledge; this is valid at prediction time but should be monitored for policy changes.
- Probability calibration, cost-sensitive thresholding, temporal cross-validation, drift monitoring, fairness/geographic review, and online feature validation should precede deployment.
- This model supports prioritization; predictive associations are not causal explanations.
