"""Run reproducible exploratory analysis against the Olist PostgreSQL database."""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, PercentFormatter
import numpy as np
import pandas as pd

from .data_loader import load_analytical_datasets

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = PROJECT_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
DATA_DIR = REPORTS_DIR / "data"
ELIGIBLE_STATUSES = {"canceled", "unavailable"}
LOGGER = logging.getLogger(__name__)

COLORS = {"blue": "#2563EB", "navy": "#17324D", "orange": "#F59E0B", "red": "#DC2626", "green": "#16A34A", "gray": "#64748B"}


def prepare_features(datasets: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Create documented, contemporaneous EDA variables without future leakage."""
    orders = datasets["orders"].copy()
    date_columns = ["purchase_timestamp", "approved_at", "delivered_carrier_at", "delivered_customer_at", "estimated_delivery_at"]
    for column in date_columns:
        orders[column] = pd.to_datetime(orders[column], errors="coerce")
    purchase = orders["purchase_timestamp"]
    orders["purchase_year"] = purchase.dt.year
    orders["purchase_month"] = purchase.dt.month
    orders["purchase_year_month"] = purchase.dt.to_period("M").dt.to_timestamp()
    orders["purchase_day_of_week"] = purchase.dt.day_name()
    orders["purchase_hour"] = purchase.dt.hour
    orders["delivery_days"] = (orders["delivered_customer_at"] - purchase).dt.total_seconds() / 86400
    orders["estimated_delivery_days"] = (orders["estimated_delivery_at"] - purchase).dt.total_seconds() / 86400
    orders["delivery_delay_days"] = (orders["delivered_customer_at"] - orders["estimated_delivery_at"]).dt.total_seconds() / 86400
    orders["is_late_delivery"] = orders["delivery_delay_days"].gt(0).where(orders["delivery_delay_days"].notna())

    customers = datasets["customers"].copy()
    customers["first_purchase"] = pd.to_datetime(customers["first_purchase"], errors="coerce")
    customers["last_purchase"] = pd.to_datetime(customers["last_purchase"], errors="coerce")
    customers["customer_order_count"] = customers["order_count"]
    customers["is_repeat_customer"] = customers["customer_order_count"] > 1

    reviews = datasets["reviews"].copy()
    reviews["review_creation_date"] = pd.to_datetime(reviews["review_creation_date"], errors="coerce")
    reviews["review_answer_timestamp"] = pd.to_datetime(reviews["review_answer_timestamp"], errors="coerce")
    datasets.update({"orders": orders, "customers": customers, "reviews": reviews})
    return datasets


def eligible_orders(orders: pd.DataFrame) -> pd.DataFrame:
    return orders.loc[~orders["order_status"].isin(ELIGIBLE_STATUSES)].copy()


def _style(ax: plt.Axes, title: str, xlabel: str = "", ylabel: str = "") -> None:
    ax.set_title(title, loc="left", fontsize=14, fontweight="bold", pad=12)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.2)


def _save(fig: plt.Figure, filename: str) -> None:
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / filename, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def generate_figures(datasets: dict[str, pd.DataFrame]) -> list[str]:
    """Generate portfolio figures from correctly grained analytical datasets."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    orders = eligible_orders(datasets["orders"])
    items = datasets["items"].loc[~datasets["items"]["order_status"].isin(ELIGIBLE_STATUSES)].copy()
    customers = datasets["customers"]
    reviews = datasets["reviews"]
    created: list[str] = []

    monthly = orders.groupby("purchase_year_month").agg(revenue=("order_value", "sum"), orders=("order_id", "count"), average_order_value=("order_value", "mean"))
    complete_monthly = monthly.loc[monthly["orders"] >= 100]
    for column, filename, title, ylabel in [
        ("revenue", "monthly_revenue.png", "Monthly revenue", "Revenue (R$)"),
        ("orders", "monthly_orders.png", "Monthly order volume", "Orders"),
        ("average_order_value", "monthly_average_order_value.png", "Average order value by month", "Average order value (R$)"),
    ]:
        fig, ax = plt.subplots(figsize=(11, 5)); ax.plot(complete_monthly.index, complete_monthly[column], color=COLORS["blue"], linewidth=2.2, marker="o", markersize=3)
        _style(ax, title, "Purchase month", ylabel)
        if column != "orders": ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"R${x:,.0f}"))
        _save(fig, filename); created.append(filename)

    fig, ax = plt.subplots(figsize=(9, 5)); cap = orders["order_value"].quantile(0.99); ax.hist(orders.loc[orders["order_value"] <= cap, "order_value"], bins=60, color=COLORS["blue"], alpha=.85)
    _style(ax, "Order value distribution (up to 99th percentile)", "Order value (R$)", "Orders"); _save(fig, "order_value_distribution.png"); created.append("order_value_distribution.png")

    category = items.groupby("category_english").agg(item_revenue=("price", "sum"), items_sold=("order_id", "size")).sort_values("item_revenue").tail(15)
    fig, ax = plt.subplots(figsize=(10, 7)); ax.barh(category.index, category["item_revenue"], color=COLORS["blue"]); ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"R${x/1e6:.1f}M")); _style(ax, "Top 15 categories by item revenue", "Item revenue", ""); _save(fig, "top_categories_revenue.png"); created.append("top_categories_revenue.png")
    category_items = items.groupby("category_english").size().sort_values().tail(15).to_frame("items_sold")
    fig, ax = plt.subplots(figsize=(10, 7)); ax.barh(category_items.index, category_items["items_sold"], color=COLORS["navy"]); _style(ax, "Items sold in top-revenue categories", "Items sold", ""); _save(fig, "top_categories_items.png"); created.append("top_categories_items.png")

    states = customers.groupby("customer_state").size().sort_values().tail(15)
    fig, ax = plt.subplots(figsize=(9, 6)); ax.barh(states.index, states, color=COLORS["blue"]); _style(ax, "Customers by state", "Unique customers", ""); _save(fig, "customers_by_state.png"); created.append("customers_by_state.png")
    repeat = customers["is_repeat_customer"].map({False: "One-time", True: "Repeat"}).value_counts()
    fig, ax = plt.subplots(figsize=(7, 5)); bars=ax.bar(repeat.index, repeat.values, color=[COLORS["gray"], COLORS["orange"]]); ax.bar_label(bars, fmt="{:,.0f}"); _style(ax, "One-time versus repeat customers", "Customer type", "Customers"); _save(fig, "repeat_customer_distribution.png"); created.append("repeat_customer_distribution.png")
    fig, ax = plt.subplots(figsize=(9, 5)); cap=customers["total_spend"].quantile(.99); ax.hist(customers.loc[customers["total_spend"] <= cap, "total_spend"], bins=60, color=COLORS["blue"]); _style(ax, "Customer spend distribution (up to 99th percentile)", "Customer spend (R$)", "Customers"); _save(fig, "customer_spend_distribution.png"); created.append("customer_spend_distribution.png")
    frequency=customers["customer_order_count"].value_counts().sort_index(); fig, ax=plt.subplots(figsize=(8,5)); ax.bar(frequency.index.astype(str), frequency.values, color=COLORS["navy"]); ax.set_yscale("log"); _style(ax, "Orders per customer", "Order count", "Customers (log scale)"); _save(fig, "orders_per_customer.png"); created.append("orders_per_customer.png")
    customer_state=customers.groupby("customer_state")["total_spend"].sum().sort_values().tail(15); fig, ax=plt.subplots(figsize=(9,6)); ax.barh(customer_state.index, customer_state, color=COLORS["green"]); ax.xaxis.set_major_formatter(FuncFormatter(lambda x,_:f"R${x/1e6:.1f}M")); _style(ax, "Top states by customer revenue", "Revenue", ""); _save(fig, "top_states_revenue.png"); created.append("top_states_revenue.png")

    delivered = orders.loc[orders["delivery_days"].notna()].copy()
    fig, ax = plt.subplots(figsize=(9, 5)); cap=delivered["delivery_days"].quantile(.99); ax.hist(delivered.loc[delivered["delivery_days"] <= cap, "delivery_days"], bins=55, color=COLORS["green"]); _style(ax, "Delivery time distribution (up to 99th percentile)", "Delivery days", "Orders"); _save(fig, "delivery_time_distribution.png"); created.append("delivery_time_distribution.png")
    state_delivery = delivered.groupby("customer_state").agg(late_rate=("is_late_delivery", "mean"), orders=("order_id", "size")).query("orders >= 100").sort_values("late_rate")
    fig, ax = plt.subplots(figsize=(9, 7)); ax.barh(state_delivery.index, state_delivery["late_rate"], color=COLORS["red"]); ax.xaxis.set_major_formatter(PercentFormatter(1)); _style(ax, "Late delivery rate by state", "Late delivery rate", ""); _save(fig, "late_delivery_by_state.png"); created.append("late_delivery_by_state.png")
    duration_state=delivered.groupby("customer_state").agg(delivery_days=("delivery_days","mean"),orders=("order_id","size")).query("orders >= 100").sort_values("delivery_days"); fig, ax=plt.subplots(figsize=(9,7)); ax.barh(duration_state.index,duration_state["delivery_days"],color=COLORS["green"]); _style(ax,"Average delivery duration by state","Average delivery days",""); _save(fig,"delivery_duration_by_state.png"); created.append("delivery_duration_by_state.png")
    month_delivery=delivered.groupby("purchase_year_month").agg(late_rate=("is_late_delivery","mean"),orders=("order_id","size")).query("orders >= 100"); fig, ax=plt.subplots(figsize=(11,5)); ax.plot(month_delivery.index,month_delivery["late_rate"],color=COLORS["red"],marker="o",linewidth=2); ax.yaxis.set_major_formatter(PercentFormatter(1)); _style(ax,"Monthly late-delivery rate","Purchase month","Late delivery rate"); _save(fig,"monthly_delivery_performance.png"); created.append("monthly_delivery_performance.png")

    score_counts = reviews["review_score"].value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(8, 5)); bars=ax.bar(score_counts.index.astype(str), score_counts, color=COLORS["blue"]); ax.bar_label(bars, fmt="{:,.0f}"); _style(ax, "Review score distribution", "Review score", "Reviews"); _save(fig, "review_score_distribution.png"); created.append("review_score_distribution.png")
    status_reviews = reviews.dropna(subset=["delivery_status"]).groupby("delivery_status")["review_score"].agg(["mean", "count"])
    fig, ax = plt.subplots(figsize=(7, 5)); bars=ax.bar(status_reviews.index, status_reviews["mean"], color=[COLORS["red"], COLORS["green"]]); ax.bar_label(bars, fmt="%.2f"); ax.set_ylim(0, 5); _style(ax, "Average review by delivery status", "Delivery status", "Average review score"); _save(fig, "review_by_delivery_status.png"); created.append("review_by_delivery_status.png")
    review_delay = reviews.dropna(subset=["delivery_delay_days", "review_score"]).copy(); review_delay["delay_band"] = pd.cut(review_delay["delivery_delay_days"], [-np.inf, 0, 3, 7, np.inf], labels=["On time/early", "1–3 days late", "4–7 days late", ">7 days late"])
    band = review_delay.groupby("delay_band", observed=True)["review_score"].mean()
    fig, ax = plt.subplots(figsize=(9, 5)); bars=ax.bar(band.index.astype(str), band, color=[COLORS["green"], COLORS["orange"], "#F97316", COLORS["red"]]); ax.bar_label(bars, fmt="%.2f"); ax.set_ylim(0,5); _style(ax, "Review score declines as delivery delay grows", "Delivery performance", "Average review score"); _save(fig, "delay_vs_review.png"); created.append("delay_vs_review.png")

    relation = delivered.loc[(delivered["freight_value"] <= delivered["freight_value"].quantile(.99)) & (delivered["delivery_days"] <= delivered["delivery_days"].quantile(.99))]
    fig, ax = plt.subplots(figsize=(9, 6)); hb=ax.hexbin(relation["freight_value"], relation["delivery_days"], gridsize=45, mincnt=1, cmap="Blues"); fig.colorbar(hb, ax=ax, label="Orders per hexagon"); _style(ax, "Freight value versus delivery duration", "Freight value (R$)", "Delivery days"); _save(fig, "freight_vs_delivery.png"); created.append("freight_vs_delivery.png")

    order_relation=orders.dropna(subset=["order_value","freight_value"]); order_relation=order_relation[(order_relation["order_value"]<=order_relation["order_value"].quantile(.99)) & (order_relation["freight_value"]<=order_relation["freight_value"].quantile(.99))]; fig, ax=plt.subplots(figsize=(9,6)); hb=ax.hexbin(order_relation["order_value"],order_relation["freight_value"],gridsize=45,mincnt=1,cmap="Blues"); fig.colorbar(hb,ax=ax,label="Orders per hexagon"); _style(ax,"Order value versus freight value","Order value (R$)","Freight value (R$)"); _save(fig,"order_value_vs_freight.png"); created.append("order_value_vs_freight.png")
    installment=orders.dropna(subset=["maximum_installments","order_value"]).groupby("maximum_installments").agg(average_order_value=("order_value","mean"),orders=("order_id","size")).query("orders >= 20"); fig,ax=plt.subplots(figsize=(9,5)); ax.plot(installment.index,installment["average_order_value"],color=COLORS["blue"],marker="o"); _style(ax,"Order value by maximum installment count","Maximum installments","Average order value (R$)"); _save(fig,"order_value_vs_installments.png"); created.append("order_value_vs_installments.png")

    order_review=reviews.groupby("order_id",as_index=False)["review_score"].mean(); category_review=items.merge(order_review,on="order_id",how="inner").groupby("category_english").agg(average_review=("review_score","mean"),reviewed_items=("order_id","size")).query("reviewed_items >= 100").sort_values("average_review"); selected=pd.concat([category_review.head(8),category_review.tail(8)]).drop_duplicates().sort_values("average_review"); fig,ax=plt.subplots(figsize=(10,7)); ax.barh(selected.index,selected["average_review"],color=[COLORS["red"] if value<4 else COLORS["green"] for value in selected["average_review"]]); ax.set_xlim(0,5); _style(ax,"Category review scores (categories with 100+ reviewed items)","Average review score",""); _save(fig,"category_review_scores.png"); created.append("category_review_scores.png")

    price = items["price"]; fig, ax = plt.subplots(figsize=(9, 5)); ax.hist(price[price <= price.quantile(.99)], bins=60, color=COLORS["navy"]); _style(ax, "Product price distribution (up to 99th percentile)", "Item price (R$)", "Items"); _save(fig, "product_price_distribution.png"); created.append("product_price_distribution.png")
    freight = items["freight_value"]; fig, ax = plt.subplots(figsize=(9, 5)); ax.hist(freight[freight <= freight.quantile(.99)], bins=60, color=COLORS["orange"]); _style(ax, "Item freight distribution (up to 99th percentile)", "Freight value (R$)", "Items"); _save(fig, "freight_value_distribution.png"); created.append("freight_value_distribution.png")
    return created


def calculate_metrics(datasets: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, dict[str, object]]:
    """Calculate reconciled business, quality, and statistical EDA metrics."""
    orders = eligible_orders(datasets["orders"]); customers=datasets["customers"]; reviews=datasets["reviews"]
    delivered = orders.dropna(subset=["delivery_days", "delivery_delay_days"])
    monthly = orders.groupby("purchase_year_month").agg(revenue=("order_value", "sum"), orders=("order_id", "size")); complete = monthly.query("orders >= 100"); best=complete["revenue"].idxmax()
    review_delivery = reviews.dropna(subset=["delivery_delay_days", "review_score"])
    late = review_delivery[review_delivery["delivery_delay_days"] > 0]["review_score"]; ontime = review_delivery[review_delivery["delivery_delay_days"] <= 0]["review_score"]
    freight_delivery = delivered[["freight_value", "delivery_days"]].dropna()
    delay_review = review_delivery[["delivery_delay_days", "review_score"]]
    quality = datasets["quality"].iloc[0].to_dict()
    items = datasets["items"]
    major_states = delivered[delivered["customer_state"].isin(["SP", "RJ", "MG"])].groupby("customer_state")["delivery_days"].agg(["mean", "median", "count"])
    values = {
        "eligible_orders": len(orders), "unique_customers": len(customers), "revenue": orders["order_value"].sum(),
        "average_order_value": orders["order_value"].mean(), "repeat_customer_rate_pct": customers["is_repeat_customer"].mean()*100,
        "strongest_complete_month": best.strftime("%Y-%m"), "strongest_month_revenue": complete.loc[best,"revenue"], "strongest_month_orders": complete.loc[best,"orders"],
        "average_delivery_days": delivered["delivery_days"].mean(), "late_delivery_rate_pct": delivered["is_late_delivery"].mean()*100,
        "average_review_score": reviews["review_score"].mean(), "late_review_mean": late.mean(), "late_review_median": late.median(), "late_review_n": len(late),
        "ontime_review_mean": ontime.mean(), "ontime_review_median": ontime.median(), "ontime_review_n": len(ontime),
        "delay_review_pearson": delay_review.corr(method="pearson").iloc[0,1], "delay_review_spearman": delay_review.corr(method="spearman").iloc[0,1], "delay_review_n": len(delay_review),
        "freight_delivery_pearson": freight_delivery.corr(method="pearson").iloc[0,1], "freight_delivery_spearman": freight_delivery.corr(method="spearman").iloc[0,1], "freight_delivery_n": len(freight_delivery),
        "order_freight_pearson": orders[["order_value","freight_value"]].corr(method="pearson").iloc[0,1],
        "order_installments_spearman": orders[["order_value","maximum_installments"]].dropna().corr(method="spearman").iloc[0,1],
        "minimum_item_price": items["price"].min(), "maximum_item_price": items["price"].max(),
        "negative_item_prices": int(items["price"].lt(0).sum()), "negative_freight_values": int(items["freight_value"].lt(0).sum()),
        "negative_delivery_durations": int(delivered["delivery_days"].lt(0).sum()),
        "purchase_date_min": orders["purchase_timestamp"].min(), "purchase_date_max": orders["purchase_timestamp"].max(),
        "sp_delivery_mean_days": major_states.loc["SP","mean"], "rj_delivery_mean_days": major_states.loc["RJ","mean"], "mg_delivery_mean_days": major_states.loc["MG","mean"],
        **quality,
    }
    metrics = pd.DataFrame([{"metric": key, "value": value} for key, value in values.items()])
    return metrics, values


def quality_profile(datasets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Summarize dimensions, duplicates, and missing cells without deleting records."""
    keys = {"orders":"order_id", "items":["order_id","order_item_id"], "reviews":["review_id","order_id"], "customers":"customer_unique_id"}
    rows=[]
    for name in ("orders","items","reviews","customers"):
        frame=datasets[name]; key=keys[name]
        rows.append({"dataset":name,"rows":len(frame),"columns":len(frame.columns),"duplicate_rows":int(frame.duplicated().sum()),"duplicate_business_keys":int(frame.duplicated(subset=key).sum()),"missing_cells":int(frame.isna().sum().sum()),"categorical_cardinality":int(frame.select_dtypes(include=["object","string"]).nunique().sum())})
    return pd.DataFrame(rows)


def write_reports(datasets: dict[str, pd.DataFrame], metrics: pd.DataFrame, values: dict[str, object], figures: list[str]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True); metrics.to_csv(DATA_DIR / "eda_metrics.csv", index=False)
    profile=quality_profile(datasets); profile.to_csv(DATA_DIR / "data_quality_profile.csv", index=False)
    items=datasets["items"].loc[~datasets["items"]["order_status"].isin(ELIGIBLE_STATUSES)]
    top_category=items.groupby("category_english")["price"].sum().idxmax(); top_category_value=items.groupby("category_english")["price"].sum().max()
    summary=f"""# Olist Exploratory Data Analysis Summary

## Executive summary

The PostgreSQL-backed EDA covers {values['eligible_orders']:,} eligible orders and {values['unique_customers']:,} unique customers. Eligible payment revenue is R${values['revenue']:,.2f}; canceled and unavailable orders are excluded from commercial metrics.

## Dataset overview

| Dataset | Rows | Columns | Duplicate business keys | Missing cells |
|---|---:|---:|---:|---:|
""" + "\n".join(f"| {r.dataset} | {r.rows:,} | {r.columns} | {r.duplicate_business_keys} | {r.missing_cells:,} |" for r in profile.itertuples()) + f"""

## Data-quality findings

- {int(values['products_missing_category']):,} products lack a category.
- {int(values['zero_installment_payments']):,} payment records report zero installments and {int(values['undefined_payment_methods']):,} use an undefined payment method.
- {int(values['delivered_missing_timestamp']):,} delivered orders lack an actual delivery timestamp.
- Negative item prices: {int(values['negative_item_prices']):,}; negative freight values: {int(values['negative_freight_values']):,}; negative actual delivery durations: {int(values['negative_delivery_durations']):,}.
- Purchases range from {values['purchase_date_min']} to {values['purchase_date_max']}; sparse boundary months are excluded from strongest-month comparisons.
- Outliers are retained; distribution plots are visually capped at the 99th percentile and labeled accordingly.

## Customer and sales findings

- Repeat customer rate: {values['repeat_customer_rate_pct']:.2f}%.
- Strongest complete month: {values['strongest_complete_month']} with {int(values['strongest_month_orders']):,} orders and R${values['strongest_month_revenue']:,.2f} revenue.
- Average order value: R${values['average_order_value']:,.2f}.

## Product findings

- The highest item-revenue category is `{top_category}` at R${top_category_value:,.2f}. Item price is treated as category GMV so payments are not duplicated across items.

## Delivery and customer satisfaction

- Average delivery duration is {values['average_delivery_days']:.2f} days and the late-delivery rate is {values['late_delivery_rate_pct']:.2f}%.
- Late deliveries average {values['late_review_mean']:.3f} stars (median {values['late_review_median']:.1f}, n={int(values['late_review_n']):,}); on-time/early deliveries average {values['ontime_review_mean']:.3f} (median {values['ontime_review_median']:.1f}, n={int(values['ontime_review_n']):,}).

## Statistical relationships

- Delivery delay vs review score: Pearson {values['delay_review_pearson']:.3f}, Spearman {values['delay_review_spearman']:.3f}, n={int(values['delay_review_n']):,}.
- Freight value vs delivery duration: Pearson {values['freight_delivery_pearson']:.3f}, Spearman {values['freight_delivery_spearman']:.3f}, n={int(values['freight_delivery_n']):,}.
- Order value vs freight value has Pearson correlation {values['order_freight_pearson']:.3f}; order value vs maximum installments has Spearman correlation {values['order_installments_spearman']:.3f}.
- Major-state mean delivery duration: SP {values['sp_delivery_mean_days']:.2f} days, MG {values['mg_delivery_mean_days']:.2f}, and RJ {values['rj_delivery_mean_days']:.2f}.
- These are associations, not causal estimates.

## Potential ML problems

1. **Late-delivery prediction** — target: late/not late per order; pre-dispatch product, seller, geography, freight and timing features; exclude actual delivery timestamps to prevent leakage. The target is observed for delivered orders and has direct operational value.
2. **Review-score prediction** — target: ordinal review score per reviewed order; use pre-delivery order context and planned logistics, while excluding review text and actual post-outcome timing when predicting early.
3. **Repeat-purchase prediction** — target: another purchase within a fixed future window per customer snapshot; historical RFM features are useful, but temporal splitting is mandatory and the low positive rate requires careful evaluation.
4. **RFM segmentation** — unit: customer; features: recency, frequency, monetary value at a fixed snapshot. This is unsupervised and must avoid using activity after the snapshot.
5. **Sales forecasting** — target: future daily/weekly order volume or revenue; partial boundary periods, promotions unavailable in Olist, and a short history limit reliability.

## Artifacts

Generated {len(figures)} figures in `reports/figures/` and machine-readable metrics in `reports/data/eda_metrics.csv`.
"""
    (REPORTS_DIR / "eda_summary.md").write_text(summary, encoding="utf-8")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    LOGGER.info("Loading analytical datasets from PostgreSQL")
    datasets=prepare_features(load_analytical_datasets())
    for name in ("orders","items","reviews","customers"): LOGGER.info("%s_df shape: %s", name, datasets[name].shape)
    figures=generate_figures(datasets); metrics, values=calculate_metrics(datasets); write_reports(datasets, metrics, values, figures)
    LOGGER.info("Generated %d figures and EDA reports", len(figures))
    print(metrics.to_string(index=False))


if __name__ == "__main__":
    main()
