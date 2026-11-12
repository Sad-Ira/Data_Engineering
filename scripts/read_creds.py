import argparse
import sqlite3
from contextlib import closing
from pathlib import Path

from dotenv import set_key

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
DATABASE = "homeworks"


def read_access(creds_path: Path, database: str = DATABASE) -> dict[str, str]:
    if not creds_path.is_file():
        raise SystemExit(f"File {creds_path} not found, pass the path to creds.db")

    with closing(sqlite3.connect(f"{creds_path.as_uri()}?mode=ro", uri=True)) as connection:
        row = connection.execute(
            "SELECT url, port, user, pass, db_name FROM access WHERE db_name = ?",
            (database,),
        ).fetchone()
    if row is None:
        raise SystemExit(f"No access to {database} found in {creds_path}")

    host, port, user, password, db_name = row
    return {
        "DB_HOST": str(host),
        "DB_PORT": str(port),
        "DB_USER": str(user),
        "DB_PASSWORD": str(password),
        "DB_NAME": str(db_name),
    }


def save_env(access: dict[str, str], env_path: Path = ENV_PATH) -> None:
    # only the owner can read the file with the password
    env_path.touch(mode=0o600, exist_ok=True)
    for key, value in access.items():
        set_key(env_path, key, value)


def main():
    parser = argparse.ArgumentParser(
        description="Copy PostgreSQL access from creds.db to the .env file"
    )
    parser.add_argument("creds_path", type=Path, help="path to creds.db")
    args = parser.parse_args()

    access = read_access(args.creds_path.expanduser().resolve())
    save_env(access)
    print(f"Access to {access['DB_NAME']} saved to {ENV_PATH}")


if __name__ == "__main__":
    main()
