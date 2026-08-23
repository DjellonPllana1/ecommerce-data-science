"""Create the Olist schema and load the source CSV files into PostgreSQL."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.engine import Engine

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
SCHEMA_PATH = PROJECT_ROOT / "database" / "schema.sql"

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class Dataset:
    filename: str
    table: str
    columns: tuple[str, ...]
    timestamp_columns: tuple[str, ...] = ()
    rename_columns: tuple[tuple[str, str], ...] = ()
    chunk_size: int = 10_000


DATASETS = (
    Dataset("olist_customers_dataset.csv", "customers", ("customer_id", "customer_unique_id", "customer_zip_code_prefix", "customer_city", "customer_state")),
    Dataset("olist_products_dataset.csv", "products", ("product_id", "product_category_name", "product_name_lenght", "product_description_lenght", "product_photos_qty", "product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"), rename_columns=(("product_name_lenght", "product_name_length"), ("product_description_lenght", "product_description_length"))),
    Dataset("olist_sellers_dataset.csv", "sellers", ("seller_id", "seller_zip_code_prefix", "seller_city", "seller_state")),
    Dataset("product_category_name_translation.csv", "product_category_translation", ("product_category_name", "product_category_name_english")),
    Dataset("olist_geolocation_dataset.csv", "geolocation", ("geolocation_zip_code_prefix", "geolocation_lat", "geolocation_lng", "geolocation_city", "geolocation_state"), chunk_size=25_000),
    Dataset("olist_orders_dataset.csv", "orders", ("order_id", "customer_id", "order_status", "order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date", "order_delivered_customer_date", "order_estimated_delivery_date"), timestamp_columns=("order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date", "order_delivered_customer_date", "order_estimated_delivery_date")),
    Dataset("olist_order_items_dataset.csv", "order_items", ("order_id", "order_item_id", "product_id", "seller_id", "shipping_limit_date", "price", "freight_value"), timestamp_columns=("shipping_limit_date",)),
    Dataset("olist_order_payments_dataset.csv", "payments", ("order_id", "payment_sequential", "payment_type", "payment_installments", "payment_value")),
    Dataset("olist_order_reviews_dataset.csv", "reviews", ("review_id", "order_id", "review_score", "review_comment_title", "review_comment_message", "review_creation_date", "review_answer_timestamp"), timestamp_columns=("review_creation_date", "review_answer_timestamp")),
)


def get_engine() -> Engine:
    """Build a SQLAlchemy engine from the project's DATABASE_URL."""
    load_dotenv(PROJECT_ROOT / ".env")
    import os

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # Managed PostgreSQL providers expose a complete connection URL. Keeping
        # it intact also preserves provider-specific SSL query parameters.
        return create_engine(database_url, pool_pre_ping=True)

    required = ["POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_HOST", "POSTGRES_PORT"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(
            "Set DATABASE_URL or provide all PostgreSQL variables; missing: "
            f"{missing}"
        )
    database_url = URL.create(
        "postgresql+psycopg2", username=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"), host=os.getenv("POSTGRES_HOST"),
        port=int(os.environ["POSTGRES_PORT"]), database=os.getenv("POSTGRES_DB"),
    )
    return create_engine(database_url, pool_pre_ping=True)


def validate_sources() -> None:
    """Ensure every source file exists and contains the required columns."""
    missing = [item.filename for item in DATASETS if not (RAW_DATA_DIR / item.filename).is_file()]
    if missing:
        raise FileNotFoundError("Missing required CSV files: " + ", ".join(missing))

    for item in DATASETS:
        actual = set(pd.read_csv(RAW_DATA_DIR / item.filename, nrows=0).columns)
        missing_columns = set(item.columns) - actual
        if missing_columns:
            raise ValueError(f"{item.filename} is missing columns: {sorted(missing_columns)}")


def create_schema(engine: Engine) -> None:
    """Execute the version-controlled PostgreSQL schema."""
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with engine.begin() as connection:
        connection.exec_driver_sql(schema_sql)


def clear_existing_data(engine: Engine) -> None:
    """Make development reruns deterministic without duplicating source rows."""
    table_names = ", ".join(item.table for item in reversed(DATASETS))
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))


def load_dataset(engine: Engine, dataset: Dataset) -> int:
    """Load one CSV in chunks and return its inserted row count."""
    inserted = 0
    source = RAW_DATA_DIR / dataset.filename
    for frame in pd.read_csv(source, chunksize=dataset.chunk_size):
        for column in dataset.timestamp_columns:
            frame[column] = pd.to_datetime(frame[column], errors="coerce")
        if dataset.rename_columns:
            frame = frame.rename(columns=dict(dataset.rename_columns))
        frame = frame.where(pd.notna(frame), None)
        frame.to_sql(dataset.table, engine, if_exists="append", index=False, method="multi", chunksize=1_000)
        inserted += len(frame)
    return inserted


def main() -> None:
    """Validate inputs, reset the schema data, and load all datasets."""
    validate_sources()
    engine = get_engine()
    try:
        create_schema(engine)
        clear_existing_data(engine)
        for dataset in DATASETS:
            LOGGER.info("Loading %s into %s", dataset.filename, dataset.table)
            count = load_dataset(engine, dataset)
            LOGGER.info("Inserted %s rows into %s", f"{count:,}", dataset.table)
    except Exception:
        LOGGER.exception("Ingestion failed")
        raise
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
