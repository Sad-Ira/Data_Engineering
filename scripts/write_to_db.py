import os
from pathlib import Path

import pandas as pd
import pyarrow.dataset as ds
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine

ROOT = Path(__file__).resolve().parent.parent
PARQUET_PATH = ROOT / "data" / "faa_aws.parquet"
TABLE = "aibatovais"
ROWS = 100
ENV_VARS = ["DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME"]


def get_db_url() -> URL:
    load_dotenv(ROOT / ".env")
    missing = [name for name in ENV_VARS if not os.environ.get(name)]
    if missing:
        raise SystemExit(
            f"Missing {', '.join(missing)} in .env, "
            "run scripts/read_creds.py first (see README.md)"
        )

    return URL.create(
        "postgresql+psycopg2",
        username=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        database=os.environ["DB_NAME"],
    )


def read_dataset(path: Path = PARQUET_PATH, rows: int = ROWS) -> pd.DataFrame:
    if not path.is_file():
        raise SystemExit(f"File {path} not found, run python data_loader.py first")

    # read only the first rows instead of the whole file, dtypes are kept
    data = ds.dataset(path).head(rows).to_pandas()
    if len(data) != rows:
        raise ValueError(f"The dataset must contain at least {rows} rows")
    return data


def write_table(data: pd.DataFrame, url: URL, table: str = TABLE) -> None:
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            data.to_sql(table, connection, index=False, if_exists="fail")
    finally:
        engine.dispose()


def main():
    url = get_db_url()
    data = read_dataset()
    write_table(data, url)
    print(f"Written {len(data)} rows to {TABLE}")


if __name__ == "__main__":
    main()
