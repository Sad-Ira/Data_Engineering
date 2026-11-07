import os
import sqlite3
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

creds_path = Path(os.environ["CREDS_PATH"]).expanduser().resolve()
with sqlite3.connect(f"{creds_path.as_uri()}?mode=ro", uri=True) as connection:
    host, port, user, password, database = connection.execute(
        "SELECT url, port, user, pass, db_name FROM access WHERE db_name = ?",
        ("homeworks",),
    ).fetchone()

url = URL.create("postgresql+psycopg2", username=user, password=password,
                 host=host, port=int(port), database=database)
engine = create_engine(url)
data = pd.read_csv(ROOT / "data" / "faa_aws.csv", nrows=100, low_memory=False)
if len(data) != 100:
    raise ValueError("The dataset must contain at least 100 rows")

with engine.begin() as connection:
    data.to_sql("aibatovais", connection, index=False, if_exists="fail")
    count = connection.execute(text("SELECT COUNT(*) FROM aibatovais")).scalar_one()
    print(f"Written {count} rows to aibatovais")

engine.dispose()
