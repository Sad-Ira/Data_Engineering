import sqlite3

import pytest

from etl.creds import read_creds, save_env
from etl.load import LoadError
from etl import main as etl_main
from etl.main import parse_args


def test_defaults():
    args = parse_args([])
    assert args.rows == 100 and args.if_exists == "fail" and not args.skip_db


@pytest.mark.parametrize("rows", ["0", "101"])
def test_rows_limit(rows):
    with pytest.raises(SystemExit):
        parse_args(["--rows", rows])


def test_creds_to_env(tmp_path):
    creds = tmp_path / "creds.db"
    with sqlite3.connect(creds) as connection:
        connection.execute("CREATE TABLE access (url, port, user, pass, db_name)")
        connection.execute("INSERT INTO access VALUES ('host', 5432, 'me', 'p@ss', 'homeworks')")
    connection.close()

    env = tmp_path / ".env"
    env.write_text("OTHER=1\n")
    save_env(read_creds(creds), env)
    text = env.read_text()
    assert "OTHER=1" in text and "DB_PASSWORD='p@ss'" in text


def test_creds_errors(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_creds(tmp_path / "nope.db")


def test_main_reports_load_errors(monkeypatch, caplog):
    def fail(args):
        raise LoadError("bad load input")

    monkeypatch.setattr(etl_main, "run", fail)
    with pytest.raises(SystemExit) as error:
        etl_main.main([])
    assert error.value.code == 1
    assert "bad load input" in caplog.text


def test_main_does_not_hide_unexpected_value_errors(monkeypatch):
    def fail(args):
        raise ValueError("unexpected bug")

    monkeypatch.setattr(etl_main, "run", fail)
    with pytest.raises(ValueError, match="unexpected bug"):
        etl_main.main([])
