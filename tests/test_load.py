import pandas as pd
import pytest

from etl import load


def test_load_to_db_rejects_more_than_max_rows(monkeypatch):
    def unexpected_connection(*args, **kwargs):
        pytest.fail("The row limit must be checked before connecting")

    monkeypatch.setattr(load, "create_engine", unexpected_connection)
    df = pd.DataFrame({"value": range(load.MAX_ROWS + 1)})
    with pytest.raises(load.LoadError, match=rf"Only {load.MAX_ROWS} rows.*got {load.MAX_ROWS + 1}"):
        load.load_to_db(df, "table", url=None)


def test_load_to_db_accepts_max_rows(monkeypatch):
    class Engine:
        def begin(self):
            return self

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def dispose(self):
            self.disposed = True

    engine = Engine()
    monkeypatch.setattr(load, "create_engine", lambda url: engine)
    calls = []
    monkeypatch.setattr(pd.DataFrame, "to_sql", lambda self, *args, **kwargs: calls.append((args, kwargs)))
    df = pd.DataFrame({"value": range(load.MAX_ROWS)})

    assert load.load_to_db(df, "table", url=None) == load.MAX_ROWS
    assert calls == [(("table", engine), {"index": False, "if_exists": "fail"})]
    assert engine.disposed


def test_get_db_url_reports_all_missing_variables(monkeypatch):
    monkeypatch.setattr(load, "find_dotenv", lambda **kwargs: "")
    monkeypatch.setattr(load, "load_dotenv", lambda path: None)
    for name in load.ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "")

    with pytest.raises(RuntimeError) as error:
        load.get_db_url()
    assert "Missing DB_PORT, DB_USER, DB_PASSWORD, DB_NAME in .env" in str(error.value)
    assert "DB_HOST" not in str(error.value)


def test_get_db_url_reports_invalid_port(monkeypatch):
    monkeypatch.setattr(load, "find_dotenv", lambda **kwargs: "")
    monkeypatch.setattr(load, "load_dotenv", lambda path: None)
    for name in load.ENV_VARS:
        monkeypatch.setenv(name, "value")

    with pytest.raises(load.LoadError, match="DB_PORT must be an integer"):
        load.get_db_url()
