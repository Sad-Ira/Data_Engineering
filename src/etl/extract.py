"""Extract: download the raw dataset from Google Drive and read it."""

import logging
from pathlib import Path

import gdown
import pandas as pd

log = logging.getLogger(__name__)

FILE_ID = "1jlokcbHZhYYWDbnIRqdPGTLnmCJ8Upjn"
RAW_NAME = "faa_aws.csv"


def looks_like_csv(path: Path) -> bool:
    """Google Drive returns an HTML page instead of the file when the limit is reached."""
    if not path.exists() or path.stat().st_size < 1024:
        return False
    with open(path, encoding="utf-8", errors="replace") as f:
        return "," in f.readline()


def download_dataset(path: Path, file_id: str = FILE_ID) -> Path:
    """Download the CSV once, the following runs reuse the local copy."""
    if path.exists():
        log.info("File %s already exists, skipping download", path)
        return path

    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    log.info("Downloading the dataset from Google Drive, it will take a few minutes...")
    try:
        gdown.download(id=file_id, output=str(part), quiet=True)
    except Exception as error:
        part.unlink(missing_ok=True)
        raise RuntimeError(
            "Download failed, check the internet connection and run the pipeline again"
        ) from error

    if not looks_like_csv(part):
        part.unlink(missing_ok=True)
        raise RuntimeError(
            "Downloaded file does not look like a CSV, probably the Google Drive "
            "download limit is reached. Try again later"
        )

    part.rename(path)
    return path


def read_raw(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def extract(data_dir: Path) -> pd.DataFrame:
    path = download_dataset(data_dir / RAW_NAME)
    df = read_raw(path)
    log.info("Extracted %d rows x %d columns from %s", *df.shape, path)
    return df
