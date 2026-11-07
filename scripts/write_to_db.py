import os
import sqlite3
from contextlib import closing
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine

ROOT = Path(__file__).resolve().parent.parent
DATABASE = "homeworks"
TABLE = "aibatovais"
ROWS = 100


def main():
    load_dotenv(ROOT / ".env")
    creds = os.environ.get("CREDS_PATH")
    if not creds:
        raise SystemExit("Set CREDS_PATH in .env (see README.md)")

    creds_path = Path(creds).expanduser().resolve()
    with closing(sqlite3.connect(f"{creds_path.as_uri()}?mode=ro", uri=True)) as connection:
        row = connection.execute(
            "SELECT url, port, user, pass, db_name FROM access WHERE db_name = ?",
            (DATABASE,),
        ).fetchone()
    if row is None:
        raise SystemExit(f"No access to {DATABASE} found in creds.db")

    host, port, user, password, database = row
    url = URL.create("postgresql+psycopg2", username=user, password=password,
                     host=host, port=int(port), database=database)
    engine = create_engine(url)
    data = pd.read_csv(ROOT / "data" / "faa_aws.csv", nrows=ROWS, low_memory=False)
    if len(data) != ROWS:
        raise ValueError(f"The dataset must contain at least {ROWS} rows")

    with engine.begin() as connection:
        data.to_sql(TABLE, connection, index=False, if_exists="fail")
    engine.dispose()
    print(f"Written {len(data)} rows to {TABLE}")


if __name__ == "__main__":
    main()
