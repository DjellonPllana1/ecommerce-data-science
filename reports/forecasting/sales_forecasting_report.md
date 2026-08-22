# Sales and Revenue Forecasting Report

## Objective and series

Forecast daily eligible orders and payment revenue from PostgreSQL. Payments are aggregated to order grain; canceled/unavailable orders are excluded. The complete series spans 2016-09-04 to 2018-09-03 (730 days) and reconciles to R$15,739,137.01. Modeling uses 2017-01-01 through 2018-08-21 (598 days), excluding the sparse 2016 launch period and the right-censored 2018-08-22 through 2018-09-03 tail.

## Seasonality and volatility

Monday has the highest average order demand. Daily order and revenue spikes above three standard deviations occur on 2 and 2 days respectively; they are retained as possible genuine business events. Seven- and thirty-day averages show growth and changing level, while weekday effects support SeasonalNaive7.

## Backtesting

| Fold | Train start | Train end | Validation start | Validation end |
|---:|---|---|---|---|
| 1 | 2017-01-01 | 2018-04-23 | 2018-04-24 | 2018-05-23 |
| 2 | 2017-01-01 | 2018-05-23 | 2018-05-24 | 2018-06-22 |
| 3 | 2017-01-01 | 2018-06-22 | 2018-06-23 | 2018-07-22 |

| Target | Model | MAE | RMSE | sMAPE |
|---|---|---:|---:|---:|
| daily_orders | HistGradientBoostingRegressor | 48.65 | 60.89 | 25.27% |
| daily_orders | HistoricalMean | 67.10 | 80.12 | 34.31% |
| daily_orders | LinearRegression | 78.83 | 90.66 | 34.52% |
| daily_orders | NaiveLastValue | 56.69 | 66.90 | 28.74% |
| daily_orders | RandomForestRegressor | 40.70 | 52.24 | 20.33% |
| daily_orders | RollingMean7 | 48.78 | 59.00 | 24.29% |
| daily_orders | SeasonalNaive7 | 44.12 | 55.89 | 22.22% |
| daily_revenue | HistGradientBoostingRegressor | 8024.51 | 9825.60 | 23.48% |
| daily_revenue | HistoricalMean | 11879.47 | 14326.68 | 37.03% |
| daily_revenue | LinearRegression | 12826.44 | 14914.33 | 33.95% |
| daily_revenue | NaiveLastValue | 10015.22 | 11914.05 | 31.61% |
| daily_revenue | RandomForestRegressor | 8482.87 | 10405.04 | 25.57% |
| daily_revenue | RollingMean7 | 8459.17 | 10563.75 | 25.38% |
| daily_revenue | SeasonalNaive7 | 8424.68 | 10241.38 | 25.93% |

Selected orders model: **RandomForestRegressor**. Selected revenue model: **HistGradientBoostingRegressor**. Selection uses mean walk-forward MAE and prefers SeasonalNaive7 when improvement is under 1%.

## Holdout, residuals, and forecast

The final 30 days were untouched during selection. Metrics for 7-, 14-, and 30-day prefixes are stored in metadata. Residual exports support weekday and extreme-error analysis. Future point forecasts are accompanied by empirical 5th/95th percentile backtest residual bounds widened by `sqrt(1 + horizon_step/7)`; these are practical uncertainty bands, not guaranteed confidence intervals.

## Interpretation and limitations

Forecasts support staffing, fulfillment, and cash planning, but reliability degrades with horizon. The dataset lacks promotions, holidays, marketing, price changes, macroeconomics, and current marketplace conditions. Recursive errors compound, and a single historical marketplace period is inadequate for long-term claims. No future actual values are fabricated.
