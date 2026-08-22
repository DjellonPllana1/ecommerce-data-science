"""Forecasting paths and constants."""
from pathlib import Path
PROJECT_ROOT=Path(__file__).resolve().parents[3]
MODEL_DIR=PROJECT_ROOT/"models"/"forecasting"; REPORT_DIR=PROJECT_ROOT/"reports"/"forecasting"; FIGURE_DIR=REPORT_DIR/"figures"
ORDERS_MODEL_PATH=MODEL_DIR/"orders_forecast_pipeline.joblib"; REVENUE_MODEL_PATH=MODEL_DIR/"revenue_forecast_pipeline.joblib"; METADATA_PATH=MODEL_DIR/"forecast_metadata.json"
RANDOM_STATE=42; MODEL_START="2017-01-01"; MODEL_END="2018-08-21"; HOLDOUT_DAYS=30; HORIZONS=[7,14,30]
