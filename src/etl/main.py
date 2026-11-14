"""Run the whole ETL: python -m etl.main --rows 100"""

import argparse
import logging
import sys
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

from etl.creds import read_creds, save_env
from etl.extract import extract
from etl.load import MAX_ROWS, LoadError, get_db_url, load_to_db, save_parquet
from etl.transform import transform
from etl.validate import ValidationError, validate

log = logging.getLogger("etl")

CLEAN_NAME = "faa_aws_clean.parquet"


def rows_count(value: str) -> int:
    rows = int(value)
    if not 1 <= rows <= MAX_ROWS:
        raise argparse.ArgumentTypeError(f"must be from 1 to {MAX_ROWS}, got {rows}")
    return rows


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="etl",
        description="FAA Wildlife Strike ETL: download, clean, validate and load to PostgreSQL",
    )
    parser.add_argument("--rows", type=rows_count, default=MAX_ROWS,
                        help=f"how many rows to write to the database, 1-{MAX_ROWS} (default {MAX_ROWS})")
    parser.add_argument("--table", default="aibatovais",
                        help="PostgreSQL table name (default aibatovais)")
    parser.add_argument("--if-exists", choices=["fail", "replace", "append"], default="fail",
                        help="what to do if the table exists (default fail, the table is not overwritten)")
    parser.add_argument("--data-dir", type=Path, default=Path("data"),
                        help="folder for the raw CSV and the clean parquet (default data)")
    parser.add_argument("--creds", type=Path,
                        help="path to creds.db, copies the database access to .env before loading")
    parser.add_argument("--skip-db", action="store_true",
                        help="stop after the parquet file, don't connect to the database")
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> None:
    # check the database access first, so a missing .env doesn't show up after the whole run
    url = None
    if not args.skip_db:
        if args.creds:
            save_env(read_creds(args.creds.expanduser()))
            log.info("Database access saved to .env")
        url = get_db_url()

    log.info("1/4 extract")
    raw = extract(args.data_dir)

    log.info("2/4 transform")
    clean = transform(raw)

    log.info("3/4 validate")
    validate(clean)

    log.info("4/4 load")
    save_parquet(clean, args.data_dir / CLEAN_NAME)
    if url is None:
        log.info("--skip-db is set, the database is not touched")
        return
    load_to_db(clean.head(args.rows), args.table, url, args.if_exists)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        run(args)
    except (ValidationError, FileNotFoundError, LookupError, RuntimeError, LoadError,
            SQLAlchemyError) as error:
        if isinstance(error, SQLAlchemyError):
            # the full message also repeats the SQL query with all the values
            error = str(getattr(error, "orig", None) or error).strip().splitlines()[0]
        log.error("%s", error)
        sys.exit(1)
    log.info("Done")


if __name__ == "__main__":
    main()
