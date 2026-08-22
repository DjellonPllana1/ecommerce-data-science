"""K selection, PCA, and clustering evaluation helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score

from .config import RANDOM_STATE
from .preprocess import RFM_FEATURES, make_cluster_pipeline


def evaluate_k_values(frame: pd.DataFrame, k_values=range(2,9)) -> tuple[pd.DataFrame,dict[int,object]]:
    """Evaluate inertia, sampled silhouette, and minimum cluster share for k=2..8."""
    rows=[]; pipelines={}
    for k in k_values:
        pipeline=make_cluster_pipeline(k); labels=pipeline.fit_predict(frame[RFM_FEATURES]); pipelines[k]=pipeline
        counts=pd.Series(labels).value_counts(); transformed=pipeline[:-1].transform(frame[RFM_FEATURES])
        silhouette=silhouette_score(transformed,labels,sample_size=min(10000,len(frame)),random_state=RANDOM_STATE)
        rows.append({"k":k,"inertia":pipeline.named_steps["kmeans"].inertia_,"silhouette_score":silhouette,"minimum_cluster_size":int(counts.min()),"minimum_cluster_share":counts.min()/len(frame)})
    return pd.DataFrame(rows),pipelines


def select_k(results: pd.DataFrame) -> int:
    """Balance silhouette, usable cluster size, and business granularity."""
    stable=results[results.minimum_cluster_share>=.02].copy()
    if stable.empty: stable=results.copy()
    best=stable.silhouette_score.max()
    near_best=stable[stable.silhouette_score>=best-.03]
    # Prefer useful granularity among statistically similar, non-tiny solutions.
    return int(near_best.loc[near_best.k.le(6),"k"].max() if near_best.k.le(6).any() else near_best.sort_values("silhouette_score",ascending=False).iloc[0].k)


def pca_coordinates(pipeline, frame: pd.DataFrame) -> tuple[np.ndarray,np.ndarray]:
    transformed=pipeline[:-1].transform(frame[RFM_FEATURES]); pca=PCA(n_components=2,random_state=RANDOM_STATE); coordinates=pca.fit_transform(transformed)
    return coordinates,pca.explained_variance_ratio_
