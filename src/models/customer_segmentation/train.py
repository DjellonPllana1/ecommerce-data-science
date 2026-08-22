"""Run classic RFM scoring, KMeans segmentation, profiling, and persistence."""

from __future__ import annotations

import json
import logging

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import numpy as np
import pandas as pd

from .build_rfm import build_rfm_dataset
from .config import FIGURE_DIR,METADATA_PATH,MODEL_DIR,PIPELINE_PATH,RANDOM_STATE,REPORT_DIR
from .evaluate import evaluate_k_values,pca_coordinates,select_k
from .preprocess import RFM_FEATURES,add_rfm_scores
from .profile import RECOMMENDATIONS,build_cluster_profiles

LOGGER=logging.getLogger(__name__)


def save_figures(frame,results,profile,coordinates,variance) -> None:
    FIGURE_DIR.mkdir(parents=True,exist_ok=True)
    colors=plt.cm.tab10(frame.cluster_id/ max(frame.cluster_id.max(),1))
    fig,axes=plt.subplots(1,3,figsize=(15,4));
    for ax,column,title in zip(axes,RFM_FEATURES,["Recency","Frequency","Monetary"]): ax.hist(np.log1p(frame[column]),bins=50,color="#2563EB"); ax.set(title=title,xlabel=f"log1p({column})",ylabel="Customers")
    fig.suptitle("RFM distributions on transformed axes",fontweight="bold"); fig.tight_layout(); fig.savefig(FIGURE_DIR/"rfm_distributions.png",dpi=160); plt.close(fig)
    for column,filename,title in [("recency","recency_distribution.png","Customer recency"),("frequency","frequency_distribution.png","Customer purchase frequency"),("monetary","monetary_distribution.png","Customer monetary value")]:
        fig,ax=plt.subplots(figsize=(8,5)); ax.hist(np.log1p(frame[column]),bins=60,color="#2563EB"); ax.set(title=f"{title} (all values retained)",xlabel=f"log1p({column})",ylabel="Customers"); fig.tight_layout(); fig.savefig(FIGURE_DIR/filename,dpi=160); plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,5)); ax.plot(results.k,results.inertia,marker="o",color="#2563EB"); ax.set(title="KMeans elbow curve",xlabel="Number of clusters (k)",ylabel="Inertia"); fig.tight_layout(); fig.savefig(FIGURE_DIR/"elbow_curve.png",dpi=160); plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,5)); ax.plot(results.k,results.silhouette_score,marker="o",color="#16A34A"); ax.set(title="Sampled silhouette scores",xlabel="Number of clusters (k)",ylabel="Silhouette score"); fig.tight_layout(); fig.savefig(FIGURE_DIR/"silhouette_scores.png",dpi=160); plt.close(fig)
    ordered=profile.sort_values("customer_count"); fig,ax=plt.subplots(figsize=(9,5)); ax.barh(ordered.cluster_name,ordered.customer_count,color="#2563EB"); ax.set(title="Cluster sizes",xlabel="Customers"); fig.tight_layout(); fig.savefig(FIGURE_DIR/"cluster_sizes.png",dpi=160,bbox_inches="tight"); plt.close(fig)
    normalized=profile.set_index("cluster_name")[["median_recency","median_frequency","median_monetary"]].copy(); normalized=(normalized-normalized.min())/(normalized.max()-normalized.min()).replace(0,1); fig,ax=plt.subplots(figsize=(10,6)); image=ax.imshow(normalized,cmap="Blues",aspect="auto"); ax.set(xticks=range(3),xticklabels=["Recency","Frequency","Monetary"],yticks=range(len(normalized)),yticklabels=normalized.index,title="Relative cluster RFM profile"); fig.colorbar(image,ax=ax,label="Min–max profile value"); fig.tight_layout(); fig.savefig(FIGURE_DIR/"cluster_rfm_profile.png",dpi=160,bbox_inches="tight"); plt.close(fig)
    sample=frame.sample(min(20000,len(frame)),random_state=RANDOM_STATE)
    for x,y,filename,title in [("recency","monetary","recency_vs_monetary_clusters.png","Recency versus monetary value"),("frequency","monetary","frequency_vs_monetary_clusters.png","Frequency versus monetary value")]:
        fig,ax=plt.subplots(figsize=(8,6)); ax.scatter(np.log1p(sample[x]),np.log1p(sample[y]),c=sample.cluster_id,cmap="tab10",s=8,alpha=.4); ax.set(title=f"{title} by cluster",xlabel=f"log1p({x})",ylabel=f"log1p({y})"); fig.tight_layout(); fig.savefig(FIGURE_DIR/filename,dpi=160); plt.close(fig)
    for column,filename,title in [("revenue_share","segment_revenue_share.png","Revenue share by cluster"),("customer_percentage","segment_customer_share.png","Customer share by cluster")]:
        ordered=profile.sort_values(column); fig,ax=plt.subplots(figsize=(9,5)); ax.barh(ordered.cluster_name,ordered[column]/100,color="#2563EB"); ax.xaxis.set_major_formatter(PercentFormatter(1)); ax.set(title=title,xlabel="Share"); fig.tight_layout(); fig.savefig(FIGURE_DIR/filename,dpi=160,bbox_inches="tight"); plt.close(fig)
    pca_frame=pd.DataFrame(coordinates,columns=["PC1","PC2"]); pca_frame["cluster_id"]=frame.cluster_id.to_numpy(); sample_idx=np.random.default_rng(RANDOM_STATE).choice(len(pca_frame),min(20000,len(pca_frame)),replace=False); plot=pca_frame.iloc[sample_idx]; fig,ax=plt.subplots(figsize=(8,6)); scatter=ax.scatter(plot.PC1,plot.PC2,c=plot.cluster_id,cmap="tab10",s=8,alpha=.4); ax.set(title=f"PCA cluster view ({variance.sum():.1%} variance shown)",xlabel=f"PC1 ({variance[0]:.1%})",ylabel=f"PC2 ({variance[1]:.1%})"); fig.colorbar(scatter,ax=ax,label="Cluster ID"); fig.tight_layout(); fig.savefig(FIGURE_DIR/"pca_cluster_visualization.png",dpi=160); plt.close(fig)


def write_report(frame,statistics,skew,rule_distribution,results,selected_k,profile,variance) -> None:
    stat_lines="\n".join(f"| {name} | {statistics.loc[name,'mean']:.2f} | {statistics.loc[name,'50%']:.2f} | {statistics.loc[name,'std']:.2f} | {statistics.loc[name,'min']:.2f} | {statistics.loc[name,'max']:.2f} | {skew[name]:.2f} |" for name in RFM_FEATURES)
    rule_lines="\n".join(f"| {r.rfm_segment} | {r.customers:,} | {r.customer_share:.2f}% |" for r in rule_distribution.itertuples())
    k_lines="\n".join(f"| {int(r.k)} | {r.silhouette_score:.4f} | {r.inertia:,.0f} | {r.minimum_cluster_size:,} | {r.minimum_cluster_share:.2%} |" for r in results.itertuples())
    profile_lines="\n".join(f"| {r.cluster_name} | {r.customer_count:,} | {r.customer_percentage:.2f}% | {r.median_recency:.1f} | {r.median_frequency:.1f} | R${r.median_monetary:,.2f} | R${r.total_revenue:,.2f} | {r.revenue_share:.2f}% | {r.repeat_customer_rate:.2%} | {r.top_customer_states} |" for r in profile.itertuples())
    action_lines="\n".join(f"- **{name}:** {RECOMMENDATIONS.get(name,'Test tailored lifecycle messaging and measure incremental response.')}" for name in profile.cluster_name)
    reference=frame.reference_date.iloc[0].date(); report=f"""# Customer Segmentation Report

## Business objective

Segment Olist customers for retention, onboarding, reactivation, and value-focused marketing using fixed-snapshot RFM behavior. Clusters are analytical groupings, not objectively real customer types.

## Customer population and RFM methodology

The read-only PostgreSQL extract contains {len(frame):,} unique customers and excludes canceled/unavailable orders. Payments are aggregated to order grain before customer totals. The fixed reference date is **{reference}**, one day after the final eligible purchase. Total monetary value is **R${frame.monetary.sum():,.2f}**, reconciling to the eligible-order SQL revenue.

| Feature | Mean | Median | Std. dev. | Minimum | Maximum | Skewness |
|---|---:|---:|---:|---:|---:|---:|
{stat_lines}

Extreme values are retained. Frequency and monetary are log1p-transformed for clustering; all three RFM features are standardized.

## Rule-based segmentation

Recency and monetary use rank-based quintiles. Frequency uses explicit order-count bands because one-time purchasing dominates and duplicate quantile boundaries would be misleading.

| RFM segment | Customers | Share |
|---|---:|---:|
{rule_lines}

## KMeans selection

Silhouette uses a reproducible 10,000-customer sample to avoid quadratic full-dataset cost. Selection considers silhouette, a minimum 2% cluster share, and useful granularity among solutions within 0.03 of the best silhouette.

| k | Silhouette | Inertia | Smallest cluster | Smallest share |
|---:|---:|---:|---:|---:|
{k_lines}

Selected **k={selected_k}**, with silhouette **{results.set_index('k').loc[selected_k,'silhouette_score']:.4f}**.

## Cluster profiles

| Cluster | Customers | Customer share | Median R | Median F | Median M | Revenue | Revenue share | Repeat rate | Top states |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
{profile_lines}

## Business recommendations

{action_lines}

## PCA visualization

The first two components explain {variance.sum():.2%} of transformed RFM variance. PCA is used only for visualization and does not prove cluster quality.

## Limitations

- The historical Olist window is short and customers observed late have less opportunity to repeat.
- RFM captures observed transactions but not acquisition channel, margin, browsing, campaign exposure, or household identity.
- Cluster names are post-hoc interpretations and should be validated through campaign experiments.
- One-time purchasing dominates, limiting the discriminatory power of Frequency.
- Segment stability should be tested across rolling reference dates before operational use.
"""
    (REPORT_DIR/"customer_segmentation_report.md").write_text(report,encoding="utf-8")


def _json_default(value):
    if isinstance(value,(np.integer,)): return int(value)
    if isinstance(value,(np.floating,)): return float(value)
    if isinstance(value,pd.Timestamp): return value.isoformat()
    raise TypeError(type(value))


def main() -> None:
    logging.basicConfig(level=logging.INFO,format="%(levelname)s: %(message)s"); MODEL_DIR.mkdir(parents=True,exist_ok=True); REPORT_DIR.mkdir(parents=True,exist_ok=True)
    frame=add_rfm_scores(build_rfm_dataset()); statistics=frame[RFM_FEATURES].describe().T; skew=frame[RFM_FEATURES].skew(); statistics.assign(skewness=skew).to_csv(REPORT_DIR/"rfm_statistics.csv")
    if abs(frame.monetary.sum()-15739137.01)>.01: raise ValueError(f"Monetary reconciliation failed: {frame.monetary.sum()}")
    rule_distribution=frame.groupby("rfm_segment").size().rename("customers").reset_index(); rule_distribution["customer_share"]=100*rule_distribution.customers/len(frame); rule_distribution=rule_distribution.sort_values("customers",ascending=False); rule_distribution.to_csv(REPORT_DIR/"rule_segment_distribution.csv",index=False)
    results,pipelines=evaluate_k_values(frame); selected_k=select_k(results); pipeline=pipelines[selected_k]; frame["cluster_id"]=pipeline.predict(frame[RFM_FEATURES]); profile,names=build_cluster_profiles(frame); frame["cluster_name"]=frame.cluster_id.map(names)
    profile.to_csv(REPORT_DIR/"cluster_profiles.csv",index=False); results.to_csv(REPORT_DIR/"k_selection_metrics.csv",index=False); pd.crosstab(frame.rfm_segment,frame.cluster_name,normalize="index").to_csv(REPORT_DIR/"rule_vs_cluster.csv")
    export=frame[["customer_unique_id","recency","frequency","monetary","rfm_segment","cluster_id","cluster_name"]]; export.to_csv(REPORT_DIR/"customer_segments.csv",index=False)
    coordinates,variance=pca_coordinates(pipeline,frame); save_figures(frame,results,profile,coordinates,variance); joblib.dump(pipeline,PIPELINE_PATH)
    metadata={"reference_date":frame.reference_date.iloc[0],"selected_k":selected_k,"features":RFM_FEATURES,"transformations":"log1p each RFM feature, then StandardScaler","cluster_names":names,"cluster_profiles":profile.to_dict(orient="records"),"silhouette_score":results.set_index("k").loc[selected_k,"silhouette_score"],"pca_explained_variance":variance.tolist(),"customer_count":len(frame),"monetary_total":frame.monetary.sum()}
    METADATA_PATH.write_text(json.dumps(metadata,indent=2,default=_json_default),encoding="utf-8"); write_report(frame,statistics,skew,rule_distribution,results,selected_k,profile,variance)
    LOGGER.info("Customers=%s reference=%s selected_k=%s silhouette=%.4f",f"{len(frame):,}",frame.reference_date.iloc[0].date(),selected_k,metadata["silhouette_score"]); print(profile.to_string(index=False))


if __name__=="__main__": main()
