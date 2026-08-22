"""Paths and reproducibility settings for customer segmentation."""

from pathlib import Path

PROJECT_ROOT=Path(__file__).resolve().parents[3]
MODEL_DIR=PROJECT_ROOT/"models"/"customer_segmentation"
REPORT_DIR=PROJECT_ROOT/"reports"/"segmentation"
FIGURE_DIR=REPORT_DIR/"figures"
PIPELINE_PATH=MODEL_DIR/"rfm_cluster_pipeline.joblib"
METADATA_PATH=MODEL_DIR/"cluster_metadata.json"
RANDOM_STATE=42
