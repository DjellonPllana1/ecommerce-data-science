"""Evaluation, threshold selection, plots, and error analysis helpers."""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (average_precision_score, balanced_accuracy_score,
    confusion_matrix, f1_score, precision_recall_curve, precision_score,
    recall_score, roc_auc_score, roc_curve)


def classification_metrics(y_true, probability, threshold: float) -> dict[str, float | int]:
    prediction = (np.asarray(probability) >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, prediction, labels=[0, 1]).ravel()
    return {
        "pr_auc": average_precision_score(y_true, probability), "roc_auc": roc_auc_score(y_true, probability),
        "precision": precision_score(y_true, prediction, zero_division=0), "recall": recall_score(y_true, prediction, zero_division=0),
        "f1": f1_score(y_true, prediction, zero_division=0), "balanced_accuracy": balanced_accuracy_score(y_true, prediction),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
    }


def optimize_threshold(y_true, probability) -> tuple[float, pd.DataFrame]:
    """Select the validation-only threshold maximizing F2 to emphasize recall."""
    rows=[]
    for threshold in np.arange(.05, .801, .01):
        predicted=np.asarray(probability)>=threshold
        precision=precision_score(y_true,predicted,zero_division=0); recall=recall_score(y_true,predicted,zero_division=0)
        f2=5*precision*recall/(4*precision+recall) if precision+recall else 0
        rows.append({"threshold":round(float(threshold),2),"precision":precision,"recall":recall,"f1":f1_score(y_true,predicted,zero_division=0),"f2":f2})
    table=pd.DataFrame(rows); best=table.sort_values(["f2","precision"],ascending=False).iloc[0]
    return float(best["threshold"]), table


def save_evaluation_figures(y_true, probability, threshold_table: pd.DataFrame, threshold: float, output_dir: Path) -> None:
    output_dir.mkdir(parents=True,exist_ok=True); predicted=(probability>=threshold).astype(int)
    precision,recall,_=precision_recall_curve(y_true,probability); fig,ax=plt.subplots(figsize=(7,5)); ax.plot(recall,precision,color="#2563EB"); ax.axhline(np.mean(y_true),ls="--",color="#64748B",label="Prevalence"); ax.set(xlabel="Recall",ylabel="Precision",title="Final test precision–recall curve"); ax.legend(); fig.tight_layout(); fig.savefig(output_dir/"precision_recall_curve.png",dpi=160); plt.close(fig)
    fpr,tpr,_=roc_curve(y_true,probability); fig,ax=plt.subplots(figsize=(7,5)); ax.plot(fpr,tpr,color="#2563EB"); ax.plot([0,1],[0,1],ls="--",color="#64748B"); ax.set(xlabel="False-positive rate",ylabel="True-positive rate",title="Final test ROC curve"); fig.tight_layout(); fig.savefig(output_dir/"roc_curve.png",dpi=160); plt.close(fig)
    matrix=confusion_matrix(y_true,predicted); fig,ax=plt.subplots(figsize=(6,5)); image=ax.imshow(matrix,cmap="Blues"); [ax.text(j,i,f"{matrix[i,j]:,}",ha="center",va="center",fontsize=13) for i in range(2) for j in range(2)]; ax.set(xticks=[0,1],yticks=[0,1],xticklabels=["On time","Late"],yticklabels=["On time","Late"],xlabel="Predicted",ylabel="Actual",title=f"Confusion matrix (threshold {threshold:.2f})"); fig.colorbar(image,ax=ax); fig.tight_layout(); fig.savefig(output_dir/"confusion_matrix.png",dpi=160); plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,5)); ax.plot(threshold_table.threshold,threshold_table.precision,label="Precision"); ax.plot(threshold_table.threshold,threshold_table.recall,label="Recall"); ax.plot(threshold_table.threshold,threshold_table.f2,label="F2"); ax.axvline(threshold,color="#DC2626",ls="--",label=f"Selected {threshold:.2f}"); ax.set(xlabel="Probability threshold",ylabel="Score",title="Validation threshold trade-off"); ax.legend(); fig.tight_layout(); fig.savefig(output_dir/"threshold_tradeoff.png",dpi=160); plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,5)); ax.hist(probability[y_true==0],bins=40,alpha=.65,label="On time/early"); ax.hist(probability[y_true==1],bins=40,alpha=.65,label="Late"); ax.axvline(threshold,color="#111827",ls="--"); ax.set(xlabel="Predicted late-delivery probability",ylabel="Orders",title="Predicted risk distribution"); ax.legend(); fig.tight_layout(); fig.savefig(output_dir/"predicted_risk_distribution.png",dpi=160); plt.close(fig)


def grouped_error_analysis(frame: pd.DataFrame, y_true, probability, threshold: float) -> dict[str, pd.DataFrame]:
    analysis=frame.copy(); analysis["actual"]=np.asarray(y_true); analysis["predicted"]=(np.asarray(probability)>=threshold).astype(int)
    analysis["error_type"]=np.select([(analysis.actual==0)&(analysis.predicted==1),(analysis.actual==1)&(analysis.predicted==0)], ["false_positive","false_negative"], default="correct")
    analysis["true_positive"]=(analysis.actual.eq(1)&analysis.predicted.eq(1)).astype(int)
    analysis["order_value_band"]=pd.qcut(analysis["item_value"],4,duplicates="drop")
    def summarize(column):
        return analysis.groupby(column,dropna=False,observed=True).agg(orders=("actual","size"),late_orders=("actual","sum"),late_rate=("actual","mean"),true_positives=("true_positive","sum"),false_negatives=("error_type",lambda x:(x=="false_negative").sum()),false_positives=("error_type",lambda x:(x=="false_positive").sum())).reset_index()
    results={"state":summarize("customer_state"),"value_band":summarize("order_value_band"),"category":summarize("dominant_product_category"),"month":summarize("purchase_month")}
    for table in results.values():
        # Recompute group recall from counts without relying on a custom multi-column aggregator.
        table["recall"] = table["true_positives"] / table["late_orders"].replace(0,np.nan)
        table["false_negative_rate"] = table["false_negatives"] / table["late_orders"].replace(0,np.nan)
    results["examples"]=analysis.loc[analysis.error_type!="correct",["order_id","purchase_timestamp","customer_state","dominant_product_category","item_value","actual","predicted","error_type"]].head(100)
    return results
