from unittest.mock import patch

from sqlalchemy.engine import Engine

from src.ingestion.load_data import get_engine


def test_get_engine_prefers_database_url(monkeypatch):
    url = "postgresql+psycopg2://demo:secret@db.example.com:5432/ecommerce?sslmode=require"
    monkeypatch.setenv("DATABASE_URL", url)
    for name in (
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_HOST",
        "POSTGRES_PORT",
    ):
        monkeypatch.delenv(name, raising=False)

    with patch("src.ingestion.load_data.load_dotenv"), patch(
        "src.ingestion.load_data.create_engine"
    ) as create_engine:
        engine = get_engine()

    assert engine is create_engine.return_value
    create_engine.assert_called_once_with(url, pool_pre_ping=True)


def test_get_engine_supports_split_local_configuration(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    values = {
        "POSTGRES_DB": "ecommerce",
        "POSTGRES_USER": "demo",
        "POSTGRES_PASSWORD": "secret",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)

    with patch("src.ingestion.load_data.load_dotenv"), patch(
        "src.ingestion.load_data.create_engine"
    ) as create_engine:
        engine = get_engine()

    assert engine is create_engine.return_value
    url = create_engine.call_args.args[0]
    assert str(url).replace("***", "secret") == (
        "postgresql+psycopg2://demo:secret@localhost:5432/ecommerce"
    )
    assert create_engine.call_args.kwargs == {"pool_pre_ping": True}
