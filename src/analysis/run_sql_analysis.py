"""Run one or all read-only SQL analysis files and print their result sets."""

from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.ingestion.load_data import get_engine

PROJECT_ROOT = Path(__file__).resolve().parents[2]
QUERY_DIR = PROJECT_ROOT / "database" / "queries"
ANALYSIS_PATTERN = "0[2-9]_*.sql"
EXECUTIVE_FILE = "10_executive_kpis.sql"


def analysis_files() -> list[Path]:
    """Return analysis files in their numeric execution order."""
    return sorted(QUERY_DIR.glob(ANALYSIS_PATTERN)) + [QUERY_DIR / EXECUTIVE_FILE]


def split_statements(sql: str) -> list[str]:
    """Split this project's simple SQL scripts into executable statements."""
    sql = "\n".join(line.split("--", 1)[0] for line in sql.splitlines())
    statements: list[str] = []
    current: list[str] = []
    in_single_quote = False
    for character in sql:
        if character == "'":
            in_single_quote = not in_single_quote
        if character == ";" and not in_single_quote:
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
        else:
            current.append(character)
    trailing = "".join(current).strip()
    if trailing:
        statements.append(trailing)
    return statements


def print_result(result) -> None:
    """Print a compact table for a SQLAlchemy result."""
    if not result.returns_rows:
        return
    rows = result.fetchall()
    headers = list(result.keys())
    widths = [len(str(header)) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(str(value)))
    print(" | ".join(str(header).ljust(widths[i]) for i, header in enumerate(headers)))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(" | ".join(str(value).ljust(widths[i]) for i, value in enumerate(row)))
    print(f"({len(rows)} rows)\n")


def run_file(path: Path) -> None:
    """Execute every statement in one SQL file inside a read-only transaction."""
    print(f"\n=== {path.name} ===")
    engine = get_engine()
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            connection.execute(text("SET TRANSACTION READ ONLY"))
            for number, statement in enumerate(split_statements(path.read_text(encoding="utf-8")), 1):
                print(f"-- Query {number}")
                print_result(connection.exec_driver_sql(statement))
            transaction.rollback()
    except SQLAlchemyError as exc:
        raise RuntimeError(f"Analysis failed in {path.name}: {exc}") from exc
    finally:
        engine.dispose()


def resolve_file(name: str) -> Path:
    """Resolve a user-supplied filename while keeping access inside query directory."""
    candidate = (QUERY_DIR / Path(name).name).resolve()
    if candidate.parent != QUERY_DIR.resolve() or candidate not in analysis_files():
        choices = ", ".join(path.name for path in analysis_files())
        raise ValueError(f"Unknown analysis file. Choose one of: {choices}")
    return candidate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", nargs="?", help="SQL filename; omit to run every analysis")
    args = parser.parse_args()
    for path in [resolve_file(args.file)] if args.file else analysis_files():
        run_file(path)


if __name__ == "__main__":
    main()
