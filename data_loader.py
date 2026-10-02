from pathlib import Path

import gdown
import pandas as pd

FILE_ID = "1jlokcbHZhYYWDbnIRqdPGTLnmCJ8Upjn"
DATA_PATH = Path("data") / "faa_aws.csv"


def looks_like_csv(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < 1024:
        return False
    with open(path, encoding="utf-8", errors="replace") as f:
        return "," in f.readline()


def download_dataset(path: Path = DATA_PATH) -> Path:
    if path.exists():
        print(f"File {path} already exists, skipping download")
        return path

    # папка data может ещё не существовать при первом запуске
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    print("Downloading the dataset from Google Drive, it will take a few minutes...")
    try:
        gdown.download(id=FILE_ID, output=str(part))
    except Exception:
        part.unlink(missing_ok=True)
        raise SystemExit("Download failed, check the internet connection and run the script again")

    if not looks_like_csv(part):
        part.unlink(missing_ok=True)
        raise SystemExit(
            "Downloaded file does not look like a CSV, probably the Google Drive "
            "download limit is reached. Try again later"
        )

    part.rename(path)
    return path


if __name__ == "__main__":
    path = download_dataset()

    df = pd.read_csv(path, low_memory=False)

    pd.set_option("display.max_columns", None)

    print(df.head(10))
    print(f"\nDataset size: {df.shape[0]} rows x {df.shape[1]} columns")
