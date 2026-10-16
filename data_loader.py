from pathlib import Path

import gdown
import pandas as pd

FILE_ID = "1jlokcbHZhYYWDbnIRqdPGTLnmCJ8Upjn"
DATA_PATH = Path("data") / "faa_aws.csv"
PARQUET_PATH = Path("data") / "faa_aws.parquet"


def looks_like_csv(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < 1024:
        return False
    with open(path, encoding="utf-8", errors="replace") as f:
        return "," in f.readline()


def download_dataset(path: Path = DATA_PATH) -> Path:
    if path.exists():
        print(f"File {path} already exists, skipping download")
        return path

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


def read_dataset(path: Path = DATA_PATH) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def convert_types(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["INCIDENT_DATE"] = pd.to_datetime(df["INCIDENT_DATE"], errors="coerce")

    int_cols = [
        "INCIDENT_MONTH", "INCIDENT_YEAR", "AC_MASS", "NUM_ENGS",
        "NUM_SEEN", "NUM_STRUCK", "NR_INJURIES", "NR_FATALITIES",
    ]
    for col in int_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    float_cols = [
        "AIRPORT_LATITUDE", "AIRPORT_LONGITUDE", "HEIGHT", "SPEED",
        "DISTANCE", "AOS",
        "COST_REPAIRS", "COST_OTHER",
        "COST_REPAIRS_INFL_ADJ", "COST_OTHER_INFL_ADJ",
    ]
    for col in float_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    bool_cols = [
        "INDICATED_DAMAGE", "INGESTED_OTHER", "OUT_OF_RANGE_SPECIES", "TRANSFER",
        "STR_RAD", "DAM_RAD", "STR_WINDSHLD", "DAM_WINDSHLD",
        "STR_NOSE", "DAM_NOSE", "STR_ENG1", "DAM_ENG1", "ING_ENG1",
        "STR_ENG2", "DAM_ENG2", "ING_ENG2", "STR_ENG3", "DAM_ENG3", "ING_ENG3",
        "STR_ENG4", "DAM_ENG4", "ING_ENG4", "STR_PROP", "DAM_PROP",
        "STR_WING_ROT", "DAM_WING_ROT", "STR_FUSE", "DAM_FUSE",
        "STR_LG", "DAM_LG", "STR_TAIL", "DAM_TAIL",
        "STR_LGHTS", "DAM_LGHTS", "STR_OTHER", "DAM_OTHER",
        "REMAINS_COLLECTED", "REMAINS_SENT",
    ]
    for col in bool_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("boolean")

    category_cols = [
        "TIME_OF_DAY", "STATE", "FAAREGION", "AC_CLASS", "TYPE_ENG",
        "PHASE_OF_FLIGHT", "SKY", "PRECIPITATION", "DAMAGE_LEVEL",
        "EFFECT", "SIZE", "WARNED",
    ]
    for col in category_cols:
        df[col] = df[col].astype("category")

    return df


def save_parquet(df: pd.DataFrame, path: Path = PARQUET_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)


if __name__ == "__main__":
    path = download_dataset()

    df = read_dataset(path)
    df = convert_types(df)
    save_parquet(df)

    pd.set_option("display.max_columns", None)

    print(df.head(10))
    print(f"\nDataset size: {df.shape[0]} rows x {df.shape[1]} columns")
    print("\nColumn dtypes:")
    print(df.dtypes.to_string())

    csv_mb = path.stat().st_size / 1024 / 1024
    parquet_mb = PARQUET_PATH.stat().st_size / 1024 / 1024
    print(f"\nSaved {PARQUET_PATH} ({parquet_mb:.1f} MB vs {csv_mb:.0f} MB for CSV)")
