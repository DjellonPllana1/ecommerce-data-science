"""Train, backtest, select, persist, and report daily forecasting models."""
from __future__ import annotations
import json,logging
import joblib,matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np,pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor,RandomForestRegressor
from sklearn.linear_model import LinearRegression
from .baselines import BASELINES,baseline_forecast
from .build_series import build_daily_series
from .config import *
from .evaluate import evaluate_candidates,folds,metrics
from .features import FEATURES,make_features,recursive_model_forecast
LOGGER=logging.getLogger(__name__)
def factories(): return {"LinearRegression":lambda:LinearRegression(),"RandomForestRegressor":lambda:RandomForestRegressor(n_estimators=250,max_depth=14,min_samples_leaf=3,n_jobs=-1,random_state=RANDOM_STATE),"HistGradientBoostingRegressor":lambda:HistGradientBoostingRegressor(max_iter=200,learning_rate=.06,max_leaf_nodes=31,l2_regularization=1,random_state=RANDOM_STATE)}
def choose_model(summary):
    best=summary.sort_values("mae").iloc[0]; seasonal=summary[summary.model=="SeasonalNaive7"].iloc[0]
    # Prefer the simpler seasonal baseline when the best improvement is under 1%.
    return "SeasonalNaive7" if (seasonal.mae-best.mae)/seasonal.mae<.01 else str(best.model)
def fit_artifact(name,series):
    if name in BASELINES:return {"kind":"baseline","model_name":name,"history":series}
    model=factories()[name](); data=make_features(series); model.fit(data[FEATURES],data.target); return {"kind":"model","model_name":name,"model":model,"history":series}
def artifact_forecast(artifact,history,horizon): return baseline_forecast(artifact["model_name"],history,horizon) if artifact["kind"]=="baseline" else recursive_model_forecast(artifact["model"],history,horizon)
def plot_history(modeling):
    FIGURE_DIR.mkdir(parents=True,exist_ok=True)
    for col,file,title,ylabel in [("daily_orders","daily_orders_history.png","Daily eligible orders","Orders"),("daily_revenue","daily_revenue_history.png","Daily eligible revenue","Revenue (R$)")]:
        fig,ax=plt.subplots(figsize=(12,5)); ax.plot(modeling.index,modeling[col],alpha=.45,color="#64748B"); ax.plot(modeling[col].rolling(30).mean(),color="#2563EB",label="30-day mean"); ax.set(title=title,xlabel="Date",ylabel=ylabel); ax.legend(); fig.tight_layout(); fig.savefig(FIGURE_DIR/file,dpi=160); plt.close(fig)
    weekday=modeling.groupby(modeling.index.day_name())[["daily_orders","daily_revenue"]].mean().reindex(["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]); fig,ax=plt.subplots(figsize=(9,5)); ax.bar(weekday.index,weekday.daily_orders,color="#2563EB"); ax.tick_params(axis="x",rotation=30); ax.set(title="Average orders by weekday",ylabel="Average daily orders"); fig.tight_layout(); fig.savefig(FIGURE_DIR/"weekly_seasonality.png",dpi=160); plt.close(fig)
    monthly=modeling.resample("MS").agg({"daily_orders":"sum","daily_revenue":"sum"}); fig,ax=plt.subplots(figsize=(11,5)); ax.plot(monthly.index,monthly.daily_orders,marker="o",color="#2563EB"); ax.set(title="Monthly order trend",ylabel="Orders",xlabel="Month"); fig.tight_layout(); fig.savefig(FIGURE_DIR/"monthly_trend.png",dpi=160); plt.close(fig)
    for col,file,title in [("daily_orders","rolling_orders.png","Order rolling averages"),("daily_revenue","rolling_revenue.png","Revenue rolling averages")]:
        fig,ax=plt.subplots(figsize=(12,5)); ax.plot(modeling[col].rolling(7).mean(),label="7-day"); ax.plot(modeling[col].rolling(30).mean(),label="30-day"); ax.set(title=title,xlabel="Date"); ax.legend(); fig.tight_layout(); fig.savefig(FIGURE_DIR/file,dpi=160); plt.close(fig)
def plot_results(target,backpred,summary,winner,holdout_actual,holdout_pred,future):
    suffix="orders" if target=="daily_orders" else "revenue"
    selected=backpred[backpred.model==winner]; fig,ax=plt.subplots(figsize=(12,5)); ax.plot(selected.date,selected.actual,color="#111827",label="Actual"); ax.plot(selected.date,selected.predicted,color="#2563EB",label="Backtest forecast"); ax.set(title=f"Walk-forward backtest: {suffix}",xlabel="Date"); ax.legend(); fig.tight_layout(); fig.savefig(FIGURE_DIR/f"backtest_{suffix}.png",dpi=160); plt.close(fig)
    ordered=summary.sort_values("mae"); fig,ax=plt.subplots(figsize=(9,5)); ax.barh(ordered.model,ordered.mae,color="#2563EB"); ax.set(title=f"Average backtest MAE: {suffix}",xlabel="MAE"); fig.tight_layout(); fig.savefig(FIGURE_DIR/f"model_comparison_{suffix}.png",dpi=160,bbox_inches="tight"); plt.close(fig)
    if target=="daily_revenue":
        residual=holdout_actual.values-holdout_pred.values; fig,axes=plt.subplots(1,2,figsize=(12,4)); axes[0].plot(holdout_actual.index,residual); axes[0].axhline(0,color="black",lw=1); axes[0].set(title="Holdout residuals over time"); axes[1].hist(residual,bins=20,color="#2563EB"); axes[1].set(title="Holdout residual distribution"); fig.tight_layout(); fig.savefig(FIGURE_DIR/"forecast_residuals.png",dpi=160); plt.close(fig)
def future_plot(history,future,horizon,file):
    fig,ax=plt.subplots(figsize=(11,5)); ax.plot(history.tail(60).index,history.tail(60),label="History",color="#111827"); ax.plot(future.date,future.predicted_orders,label="Forecast",color="#2563EB"); ax.fill_between(future.date,future.orders_lower_bound,future.orders_upper_bound,alpha=.2,color="#2563EB",label="Practical interval"); ax.set(title=f"{horizon}-day order forecast",xlabel="Date",ylabel="Orders"); ax.legend(); fig.tight_layout(); fig.savefig(FIGURE_DIR/file,dpi=160); plt.close(fig)
def main():
    logging.basicConfig(level=logging.INFO,format="%(levelname)s: %(message)s"); MODEL_DIR.mkdir(parents=True,exist_ok=True); REPORT_DIR.mkdir(parents=True,exist_ok=True)
    full,modeling=build_daily_series(); plot_history(modeling); all_rows=[]; metadata={"frequency":"daily","features":FEATURES,"horizons":HORIZONS,"full_historical_range":[str(full.date.min().date()),str(full.date.max().date())],"modeling_range":[str(modeling.index.min().date()),str(modeling.index.max().date())],"full_observations":len(full),"modeling_observations":len(modeling),"total_revenue":full.daily_revenue.sum(),"folds":{},"selected_models":{},"backtest_metrics":{},"holdout_metrics":{},"uncertainty":{},"limitations":["Sparse 2016 launch period and right-censored 2018-08-22 through 2018-09-03 tail excluded from modeling","No promotions, holidays, marketing, traffic, or macroeconomic regressors","Intervals use empirical backtest residuals and heuristic horizon widening"]}
    artifacts={}; residual_tables={}
    for target in ["daily_orders","daily_revenue"]:
        series=modeling[target]; bt,preds=evaluate_candidates(series,factories()); bt["target"]=target; all_rows.append(bt); summary=bt.groupby("model")[["mae","rmse","mape","smape"]].mean().reset_index(); winner=choose_model(summary); metadata["selected_models"][target]=winner; metadata["backtest_metrics"][target]=summary.set_index("model").to_dict(orient="index")
        metadata["folds"][target]=[{"train_start":str(tr.index.min().date()),"train_end":str(tr.index.max().date()),"validation_start":str(v.index.min().date()),"validation_end":str(v.index.max().date())} for tr,v in folds(series)]
        train=series.iloc[:-HOLDOUT_DAYS]; holdout=series.iloc[-HOLDOUT_DAYS:]; selection_artifact=fit_artifact(winner,train); hp=artifact_forecast(selection_artifact,train,HOLDOUT_DAYS)
        metadata["holdout_metrics"][target]={str(h):metrics(holdout.iloc[:h],hp.iloc[:h]) for h in HORIZONS}
        selected_preds=preds[preds.model==winner].copy(); residual=selected_preds.actual-selected_preds.predicted; metadata["uncertainty"]["orders" if target=="daily_orders" else "revenue"]=[float(residual.quantile(.05)),float(residual.quantile(.95))]
        residual_tables[target]=pd.DataFrame({"date":holdout.index,"actual":holdout.values,"predicted":hp.values,"residual":holdout.values-hp.values,"weekday":holdout.index.day_name()}); residual_tables[target].to_csv(REPORT_DIR/f"holdout_residuals_{target}.csv",index=False)
        final_artifact=fit_artifact(winner,series); artifacts[target]=final_artifact; plot_results(target,preds,summary,winner,holdout,hp,None)
    comparison=pd.concat(all_rows); comparison.to_csv(REPORT_DIR/"model_comparison.csv",index=False); joblib.dump(artifacts["daily_orders"],ORDERS_MODEL_PATH); joblib.dump(artifacts["daily_revenue"],REVENUE_MODEL_PATH); METADATA_PATH.write_text(json.dumps(metadata,indent=2,default=lambda x:float(x) if isinstance(x,(np.floating,np.integer)) else str(x)),encoding="utf-8")
    from .forecast import generate_forecast
    future=generate_forecast(30); future.to_csv(REPORT_DIR/"future_forecast.csv",index=False); future_plot(modeling.daily_orders,future.iloc[:7],7,"forecast_7_days.png"); future_plot(modeling.daily_orders,future,30,"forecast_30_days.png")
    weekday=modeling.groupby(modeling.index.day_name()).agg(orders=("daily_orders","mean"),revenue=("daily_revenue","mean")).sort_values("orders",ascending=False); spikes={c:int((modeling[c]>modeling[c].mean()+3*modeling[c].std()).sum()) for c in ["daily_orders","daily_revenue"]}
    avg=comparison.groupby(["target","model"])[["mae","rmse","mape","smape"]].mean().reset_index(); lines="\n".join(f"| {r.target} | {r.model} | {r.mae:.2f} | {r.rmse:.2f} | {r.smape:.2f}% |" for r in avg.itertuples()); fold_lines="\n".join(f"| {i+1} | {f['train_start']} | {f['train_end']} | {f['validation_start']} | {f['validation_end']} |" for i,f in enumerate(metadata['folds']['daily_orders'])); report=f"""# Sales and Revenue Forecasting Report

## Objective and series

Forecast daily eligible orders and payment revenue from PostgreSQL. Payments are aggregated to order grain; canceled/unavailable orders are excluded. The complete series spans {metadata['full_historical_range'][0]} to {metadata['full_historical_range'][1]} ({len(full)} days) and reconciles to R${metadata['total_revenue']:,.2f}. Modeling uses {metadata['modeling_range'][0]} through {metadata['modeling_range'][1]} ({len(modeling)} days), excluding sparse launch and incomplete tail periods.

## Seasonality and volatility

{weekday.index[0]} has the highest average order demand. Daily order and revenue spikes above three standard deviations occur on {spikes['daily_orders']} and {spikes['daily_revenue']} days respectively; they are retained as possible genuine business events. Seven- and thirty-day averages show growth and changing level, while weekday effects support SeasonalNaive7.

## Backtesting

| Fold | Train start | Train end | Validation start | Validation end |
|---:|---|---|---|---|
{fold_lines}

| Target | Model | MAE | RMSE | sMAPE |
|---|---|---:|---:|---:|
{lines}

Selected orders model: **{metadata['selected_models']['daily_orders']}**. Selected revenue model: **{metadata['selected_models']['daily_revenue']}**. Selection uses mean walk-forward MAE and prefers SeasonalNaive7 when improvement is under 1%.

## Holdout, residuals, and forecast

The final 30 days were untouched during selection. Metrics for 7-, 14-, and 30-day prefixes are stored in metadata. Residual exports support weekday and extreme-error analysis. Future point forecasts are accompanied by empirical 5th/95th percentile backtest residual bounds widened by `sqrt(1 + horizon_step/7)`; these are practical uncertainty bands, not guaranteed confidence intervals.

## Interpretation and limitations

Forecasts support staffing, fulfillment, and cash planning, but reliability degrades with horizon. The dataset lacks promotions, holidays, marketing, price changes, macroeconomics, and current marketplace conditions. Recursive errors compound, and a single historical marketplace period is inadequate for long-term claims. No future actual values are fabricated.
"""; (REPORT_DIR/"sales_forecasting_report.md").write_text(report,encoding="utf-8"); LOGGER.info("Selected orders=%s revenue=%s",metadata['selected_models']['daily_orders'],metadata['selected_models']['daily_revenue']); print(future.to_string(index=False))
if __name__=="__main__":main()
