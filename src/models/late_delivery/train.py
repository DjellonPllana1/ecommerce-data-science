"""Train, select, evaluate, document, and persist late-delivery models."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from .build_dataset import build_modeling_dataset
from .config import (FEATURES, FIGURE_DIR, IDENTIFIER, METADATA_PATH, MODEL_DIR,
    MODEL_PATH, PROHIBITED_FEATURES, RANDOM_STATE, REPORT_DIR, TARGET, TIME_COLUMN)
from .evaluate import classification_metrics, grouped_error_analysis, optimize_threshold, save_evaluation_figures
from .features import audit_features, build_preprocessor

LOGGER = logging.getLogger(__name__)


def temporal_split(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Allocate chronological 70/15/15 splits; no shuffling is performed."""
    ordered=frame.sort_values([TIME_COLUMN,IDENTIFIER]).reset_index(drop=True)
    train_end=int(len(ordered)*.70); validation_end=int(len(ordered)*.85)
    return {"train":ordered.iloc[:train_end].copy(),"validation":ordered.iloc[train_end:validation_end].copy(),"test":ordered.iloc[validation_end:].copy()}


def model_candidates() -> dict[str, Pipeline]:
    """Return modest, reproducible candidate pipelines."""
    return {
        "DummyClassifier": Pipeline([("preprocess",build_preprocessor(False)),("model",DummyClassifier(strategy="prior",random_state=RANDOM_STATE))]),
        "LogisticRegression": Pipeline([("preprocess",build_preprocessor(True)),("model",LogisticRegression(max_iter=1000,class_weight="balanced",C=.5,random_state=RANDOM_STATE))]),
        "RandomForestClassifier": Pipeline([("preprocess",build_preprocessor(False)),("model",RandomForestClassifier(n_estimators=250,max_depth=16,min_samples_leaf=5,max_features="sqrt",class_weight="balanced_subsample",n_jobs=-1,random_state=RANDOM_STATE))]),
        "HistGradientBoostingClassifier": Pipeline([("preprocess",build_preprocessor(False)),("model",HistGradientBoostingClassifier(max_iter=200,learning_rate=.08,max_leaf_nodes=31,l2_regularization=1.0,class_weight="balanced",random_state=RANDOM_STATE))]),
    }


def split_summary(splits: dict[str,pd.DataFrame]) -> pd.DataFrame:
    return pd.DataFrame([{"split":name,"rows":len(part),"start":part[TIME_COLUMN].min(),"end":part[TIME_COLUMN].max(),"late_orders":int(part[TARGET].sum()),"late_prevalence":part[TARGET].mean()} for name,part in splits.items()])


def _json_default(value):
    if isinstance(value,(np.integer,)): return int(value)
    if isinstance(value,(np.floating,)): return float(value)
    if isinstance(value,(pd.Timestamp,datetime)): return value.isoformat()
    raise TypeError(f"Not JSON serializable: {type(value)}")


def save_basic_figures(frame: pd.DataFrame, comparison: pd.DataFrame) -> None:
    FIGURE_DIR.mkdir(parents=True,exist_ok=True)
    counts=frame[TARGET].value_counts().sort_index(); fig,ax=plt.subplots(figsize=(7,5)); bars=ax.bar(["On time/early","Late"],counts.values,color=["#2563EB","#DC2626"]); ax.bar_label(bars,fmt="{:,.0f}"); ax.set(title="Late-delivery target distribution",ylabel="Orders"); fig.tight_layout(); fig.savefig(FIGURE_DIR/"target_distribution.png",dpi=160); plt.close(fig)
    validation=comparison[comparison.split=="validation"].sort_values("pr_auc"); fig,ax=plt.subplots(figsize=(9,5)); ax.barh(validation.model,validation.pr_auc,color="#2563EB"); ax.axvline(frame[TARGET].mean(),color="#64748B",ls="--",label="Overall prevalence"); ax.set(xlabel="Validation PR-AUC",title="Model comparison on future validation period"); ax.legend(); fig.tight_layout(); fig.savefig(FIGURE_DIR/"model_comparison.png",dpi=160,bbox_inches="tight"); plt.close(fig)


def write_report(frame, summary, comparison, winner, threshold, test_metrics, importance, errors) -> None:
    metrics_table=comparison.copy(); metrics_table[["pr_auc","roc_auc","precision","recall","f1","balanced_accuracy"]]=metrics_table[["pr_auc","roc_auc","precision","recall","f1","balanced_accuracy"]].round(4)
    split_lines="\n".join(f"| {r.split} | {r.rows:,} | {r.start} | {r.end} | {r.late_prevalence:.2%} |" for r in summary.itertuples())
    metric_lines="\n".join(f"| {r.model} | {r.split} | {r.pr_auc:.4f} | {r.roc_auc:.4f} | {r.precision:.4f} | {r.recall:.4f} | {r.f1:.4f} |" for r in metrics_table.itertuples())
    importance_lines="\n".join(f"| {r.feature} | {r.importance_mean:.6f} | {r.importance_std:.6f} |" for r in importance.head(15).itertuples())
    report=f"""# Late Delivery Prediction Model Report

## Business problem

Predict late-delivery risk at purchase time so operations teams can prioritize preventive action. Late deliveries are rare and costly, so PR-AUC, recall, precision, and F1 are more informative than plain accuracy.

## Dataset and target

The PostgreSQL dataset contains {len(frame):,} delivered orders at exactly one row per order. The target is 1 when actual customer delivery is later than the estimated delivery timestamp. There are {int(frame[TARGET].sum()):,} late orders ({frame[TARGET].mean():.2%}). Item, payment, product, and seller inputs are aggregated before joining.

## Leakage policy and features

The {len(FEATURES)} selected features are purchase-time calendar, location, basket, catalog, seller, checkout payment, and estimated-window attributes. Actual delivery/carrier timestamps, delivery duration/delay, reviews, target, and raw IDs are excluded. `feature_audit.csv` records prediction-time availability for every feature.

## Temporal split

| Split | Rows | Start | End | Late prevalence |
|---|---:|---|---|---:|
{split_lines}

The final test period remained untouched during model choice and validation-only threshold optimization.

## Models and validation

| Model | Split | PR-AUC | ROC-AUC | Precision | Recall | F1 |
|---|---|---:|---:|---:|---:|---:|
{metric_lines}

The winning model is **{winner}**, selected by validation PR-AUC rather than accuracy or test performance.

## Threshold and final test

Validation F2 optimization selected threshold **{threshold:.2f}**, placing extra weight on identifying late orders. On the untouched test set: PR-AUC {test_metrics['pr_auc']:.4f}, ROC-AUC {test_metrics['roc_auc']:.4f}, precision {test_metrics['precision']:.4f}, recall {test_metrics['recall']:.4f}, F1 {test_metrics['f1']:.4f}, and balanced accuracy {test_metrics['balanced_accuracy']:.4f}. Confusion matrix: TN={test_metrics['tn']:,}, FP={test_metrics['fp']:,}, FN={test_metrics['fn']:,}, TP={test_metrics['tp']:,}.

## Predictive importance

Permutation importance measures validation PR-AUC change and indicates association, not causation.

| Feature | Mean importance | Std. deviation |
|---|---:|---:|
{importance_lines}

## Error analysis

False negatives are genuinely late orders the model did not flag. Detailed state, value-band, category, month, and example error tables are saved under `reports/modeling/`. Segment results with small samples should not drive policy without uncertainty analysis.

## Limitations and production improvements

- Olist covers a historical marketplace period and may not represent current logistics.
- The database lacks live carrier capacity, weather, traffic, holidays, and seller operational load.
- Estimated delivery windows can encode existing platform logistics knowledge; this is valid at prediction time but should be monitored for policy changes.
- Probability calibration, cost-sensitive thresholding, temporal cross-validation, drift monitoring, fairness/geographic review, and online feature validation should precede deployment.
- This model supports prioritization; predictive associations are not causal explanations.
"""
    (REPORT_DIR/"late_delivery_model_report.md").write_text(report,encoding="utf-8")


def main() -> None:
    logging.basicConfig(level=logging.INFO,format="%(levelname)s: %(message)s")
    MODEL_DIR.mkdir(parents=True,exist_ok=True); REPORT_DIR.mkdir(parents=True,exist_ok=True); FIGURE_DIR.mkdir(parents=True,exist_ok=True)
    frame=build_modeling_dataset(); audit=audit_features(frame); audit.to_csv(REPORT_DIR/"feature_audit.csv",index=False)
    if set(FEATURES)&PROHIBITED_FEATURES: raise RuntimeError("Leakage audit failed")
    splits=temporal_split(frame); summary=split_summary(splits); summary.to_csv(REPORT_DIR/"temporal_split_summary.csv",index=False)
    LOGGER.info("Dataset rows=%s late=%s prevalence=%.3f%%",f"{len(frame):,}",f"{frame[TARGET].sum():,}",100*frame[TARGET].mean())
    LOGGER.info("\n%s",summary.to_string(index=False))
    candidates=model_candidates(); metric_rows=[]; validation_probabilities={}
    for name,pipeline in candidates.items():
        LOGGER.info("Training %s",name); pipeline.fit(splits["train"][FEATURES],splits["train"][TARGET])
        for split_name in ("train","validation"):
            part=splits[split_name]; probability=pipeline.predict_proba(part[FEATURES])[:,1]
            metrics=classification_metrics(part[TARGET],probability,.5); metric_rows.append({"model":name,"split":split_name,**metrics})
            if split_name=="validation": validation_probabilities[name]=probability
    comparison=pd.DataFrame(metric_rows); comparison.to_csv(REPORT_DIR/"model_metrics.csv",index=False)
    winner=(comparison[comparison.split=="validation"].sort_values(["pr_auc","recall"],ascending=False).iloc[0].model); winning_pipeline=candidates[winner]
    threshold,threshold_table=optimize_threshold(splits["validation"][TARGET],validation_probabilities[winner]); threshold_table.to_csv(REPORT_DIR/"threshold_metrics.csv",index=False)
    test_probability=winning_pipeline.predict_proba(splits["test"][FEATURES])[:,1]; test_metrics=classification_metrics(splits["test"][TARGET],test_probability,threshold)
    save_basic_figures(frame,comparison); save_evaluation_figures(splits["test"][TARGET].to_numpy(),test_probability,threshold_table,threshold,FIGURE_DIR)
    sample=splits["validation"].sample(min(10000,len(splits["validation"])),random_state=RANDOM_STATE)
    permutation=permutation_importance(winning_pipeline,sample[FEATURES],sample[TARGET],scoring="average_precision",n_repeats=3,random_state=RANDOM_STATE,n_jobs=-1)
    importance=pd.DataFrame({"feature":FEATURES,"importance_mean":permutation.importances_mean,"importance_std":permutation.importances_std}).sort_values("importance_mean",ascending=False); importance.to_csv(REPORT_DIR/"feature_importance.csv",index=False)
    top=importance.head(15).sort_values("importance_mean"); fig,ax=plt.subplots(figsize=(9,7)); ax.barh(top.feature,top.importance_mean,color="#2563EB"); ax.set(xlabel="Validation PR-AUC decrease",title="Permutation feature importance"); fig.tight_layout(); fig.savefig(FIGURE_DIR/"feature_importance.png",dpi=160,bbox_inches="tight"); plt.close(fig)
    errors=grouped_error_analysis(splits["test"],splits["test"][TARGET],test_probability,threshold)
    for name,table in errors.items(): table.to_csv(REPORT_DIR/f"error_analysis_{name}.csv",index=False)
    joblib.dump(winning_pipeline,MODEL_PATH)
    metadata={"model_name":winner,"features":FEATURES,"threshold":threshold,"created_at_utc":datetime.now(timezone.utc).isoformat(),"training_date_range":{"start":splits['train'][TIME_COLUMN].min(),"end":splits['train'][TIME_COLUMN].max()},"validation_date_range":{"start":splits['validation'][TIME_COLUMN].min(),"end":splits['validation'][TIME_COLUMN].max()},"test_date_range":{"start":splits['test'][TIME_COLUMN].min(),"end":splits['test'][TIME_COLUMN].max()},"dataset_rows":len(frame),"target_prevalence":frame[TARGET].mean(),"test_metrics":test_metrics,"leakage_audit_passed":True}
    METADATA_PATH.write_text(json.dumps(metadata,indent=2,default=_json_default),encoding="utf-8")
    write_report(frame,summary,comparison,winner,threshold,test_metrics,importance,errors)
    print(json.dumps(metadata,indent=2,default=_json_default))


if __name__ == "__main__":
    main()
