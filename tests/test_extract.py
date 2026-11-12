import pytest

from etl.extract import download_dataset


def test_download_without_file_reports_failure(tmp_path, monkeypatch):
    monkeypatch.setattr("etl.extract.gdown.download", lambda **kwargs: None)
    path = tmp_path / "data.csv"

    with pytest.raises(RuntimeError, match="without creating a file"):
        download_dataset(path)
    assert not path.exists()


def test_invalid_download_is_removed(tmp_path, monkeypatch):
    def download(**kwargs):
        from pathlib import Path

        Path(kwargs["output"]).write_text("<html>not a CSV</html>")

    monkeypatch.setattr("etl.extract.gdown.download", download)
    path = tmp_path / "data.csv"
    with pytest.raises(RuntimeError, match="does not look like a CSV"):
        download_dataset(path)
    assert not path.exists()
    assert not (tmp_path / "data.csv.part").exists()
