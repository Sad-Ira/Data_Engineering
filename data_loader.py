from pathlib import Path

import gdown
import pandas as pd

FILE_ID = "1jlokcbHZhYYWDbnIRqdPGTLnmCJ8Upjn"
DATA_PATH = Path("faa_aws.csv")


def download_dataset(path: Path = DATA_PATH) -> Path:
    if path.exists():
        print(f"File {path} already exists, skipping download")
        return path

    print("Downloading the dataset from Google Drive, it will take a few minutes...")
    gdown.download(id=FILE_ID, output=str(path))
    return path


if __name__ == "__main__":
    path = download_dataset()

    df = pd.read_csv(path, low_memory=False)

    print(df.head(10))
    print(f"\nDataset size: {df.shape[0]} rows x {df.shape[1]} columns")
