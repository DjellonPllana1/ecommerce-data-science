"""Test the configured PostgreSQL connection."""

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .load_data import get_engine


def main() -> None:
    """Connect and report the server version and active database."""
    engine = get_engine()
    try:
        with engine.connect() as connection:
            version = connection.execute(text("SELECT version()" )).scalar_one()
            database = connection.execute(text("SELECT current_database()" )).scalar_one()
        print(f"Connection successful: database={database}")
        print(f"PostgreSQL server: {version}")
    except SQLAlchemyError as exc:
        raise RuntimeError(f"Could not connect to PostgreSQL: {exc}") from exc
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
