# Customer Segmentation Report

## Business objective

Segment Olist customers for retention, onboarding, reactivation, and value-focused marketing using fixed-snapshot RFM behavior. Clusters are analytical groupings, not objectively real customer types.

## Customer population and RFM methodology

The read-only PostgreSQL extract contains 94,990 unique customers and excludes canceled/unavailable orders. Payments are aggregated to order grain before customer totals. The fixed reference date is **2018-09-04**, one day after the final eligible purchase. Total monetary value is **R$15,739,137.01**, reconciling to the eligible-order SQL revenue.

| Feature | Mean | Median | Std. dev. | Minimum | Maximum | Skewness |
|---|---:|---:|---:|---:|---:|---:|
| recency | 244.35 | 225.00 | 153.00 | 1.00 | 730.00 | 0.45 |
| frequency | 1.03 | 1.00 | 0.21 | 1.00 | 16.00 | 11.51 |
| monetary | 165.69 | 107.90 | 226.74 | 0.00 | 13664.08 | 9.11 |

Extreme values are retained. Frequency and monetary are log1p-transformed for clustering; all three RFM features are standardized.

## Rule-based segmentation

Recency and monetary use rank-based quintiles. Frequency uses explicit order-count bands because one-time purchasing dominates and duplicate quantile boundaries would be misleading.

| RFM segment | Customers | Share |
|---|---:|---:|
| Hibernating | 22,975 | 24.19% |
| Needs Attention | 18,962 | 19.96% |
| Promising | 18,399 | 19.37% |
| New Customers | 18,355 | 19.32% |
| High Value At Risk | 14,769 | 15.55% |
| Potential Loyalists | 1,114 | 1.17% |
| At Risk | 252 | 0.27% |
| Champions | 123 | 0.13% |
| Loyal Customers | 41 | 0.04% |

## KMeans selection

Silhouette uses a reproducible 10,000-customer sample to avoid quadratic full-dataset cost. Selection considers silhouette, a minimum 2% cluster share, and useful granularity among solutions within 0.03 of the best silhouette.

| k | Silhouette | Inertia | Smallest cluster | Smallest share |
|---:|---:|---:|---:|---:|
| 2 | 0.7081 | 193,526 | 2,888 | 3.04% |
| 3 | 0.3993 | 130,829 | 2,888 | 3.04% |
| 4 | 0.3915 | 84,592 | 2,888 | 3.04% |
| 5 | 0.3589 | 69,872 | 2,888 | 3.04% |
| 6 | 0.3564 | 59,704 | 2,888 | 3.04% |
| 7 | 0.3544 | 52,107 | 2,888 | 3.04% |
| 8 | 0.3505 | 46,262 | 2,888 | 3.04% |

Selected **k=2**, with silhouette **0.7081**.

## Cluster profiles

| Cluster | Customers | Customer share | Median R | Median F | Median M | Revenue | Revenue share | Repeat rate | Top states |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| One-Time Customers | 92,102 | 96.96% | 226.0 | 1.0 | R$105.65 | R$14,848,602.89 | 94.34% | 0.00% | SP, RJ, MG |
| Repeat High-Value Customers | 2,888 | 3.04% | 206.5 | 2.0 | R$225.53 | R$890,534.12 | 5.66% | 100.00% | SP, RJ, MG |

## Business recommendations

- **One-Time Customers:** Use onboarding and carefully tested second-purchase prompts, segmented further by rule-based recency and value.
- **Repeat High-Value Customers:** Protect this scarce repeat group with recognition, priority service, and personalized cross-sell offers.

## PCA visualization

The first two components explain 72.15% of transformed RFM variance. PCA is used only for visualization and does not prove cluster quality.

## Limitations

- The historical Olist window is short and customers observed late have less opportunity to repeat.
- RFM captures observed transactions but not acquisition channel, margin, browsing, campaign exposure, or household identity.
- Cluster names are post-hoc interpretations and should be validated through campaign experiments.
- One-time purchasing dominates, limiting the discriminatory power of Frequency.
- Segment stability should be tested across rolling reference dates before operational use.
