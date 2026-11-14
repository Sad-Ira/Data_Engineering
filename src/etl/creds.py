"""Copy PostgreSQL access from the SQLite database creds.db to the .env file."""

import sqlite3
from contextlib import closing
from pathlib import Path

from dotenv import set_key

DATABASE = "homeworks"


def read_creds(creds_path: Path, database: str = DATABASE) -> dict[str, str]:
    if not creds_path.is_file():
        raise FileNotFoundError(f"File {creds_path} not found, pass the path to creds.db")

    with closing(sqlite3.connect(f"{creds_path.resolve().as_uri()}?mode=ro", uri=True)) as connection:
        row = connection.execute(
            "SELECT url, port, user, pass, db_name FROM access WHERE db_name = ?",
            (database,),
        ).fetchone()
    if row is None:
        raise LookupError(f"No access to {database} found in {creds_path}")

    host, port, user, password, db_name = row
    return {
        "DB_HOST": str(host),
        "DB_PORT": str(port),
        "DB_USER": str(user),
        "DB_PASSWORD": str(password),
        "DB_NAME": str(db_name),
    }


def save_env(access: dict[str, str], env_path: Path = Path(".env")) -> None:
    """Add the access to .env, other variables in the file are kept."""
    # only the owner can read the file with the password
    env_path.touch(mode=0o600, exist_ok=True)
    for key, value in access.items():
        set_key(env_path, key, value)
