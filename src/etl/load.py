"""Load: save the clean dataset to parquet and write a sample to PostgreSQL."""

import logging
import os
from pathlib import Path

import pandas as pd
from dotenv import find_dotenv, load_dotenv
from sqlalchemy import URL, create_engine

log = logging.getLogger(__name__)

MAX_ROWS = 100
ENV_VARS = ["DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME"]


def save_parquet(df: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    log.info("Saved %s (%.1f MB)", path, path.stat().st_size / 1024 / 1024)
    return path


def get_db_url() -> URL:
    """Build the connection URL from the DB_* variables in the environment or .env."""
    load_dotenv(find_dotenv(usecwd=True))
    missing = [name for name in ENV_VARS if not os.environ.get(name)]
    if missing:
        raise RuntimeError(
            f"Missing {', '.join(missing)} in .env, run the pipeline with "
            "--creds /path/to/creds.db once (see README.md)"
        )

    return URL.create(
        "postgresql+psycopg2",
        username=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        database=os.environ["DB_NAME"],
    )


def load_to_db(df: pd.DataFrame, table: str, url: URL, if_exists: str = "fail") -> int:
    if len(df) > MAX_ROWS:
        raise ValueError(f"Only {MAX_ROWS} rows can be loaded to the database, got {len(df)}")

    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            df.to_sql(table, connection, index=False, if_exists=if_exists)
    finally:
        engine.dispose()
    log.info("Written %d rows to the table %s", len(df), table)
    return len(df)
