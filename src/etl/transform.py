"""Transform: clean the raw data and cast the columns to proper dtypes.

Every step follows a recommendation from the EDA (notebooks/EDA.ipynb, section 8).
Contradictions that can't be fixed for sure are flagged, not changed.
"""

import logging

import pandas as pd

log = logging.getLogger(__name__)

# one value for all rows, nothing to analyse
CONSTANT_COLUMNS = ["REPORTED_NAME", "REPORTED_TITLE", "TRANSFER"]

# missing values hidden behind codes
PLACEHOLDERS = {
    "AIRPORT_ID": "ZZZZ",
    "AIRPORT": "UNKNOWN",
    "OPID": "UNK",
    "OPERATOR": "UNKNOWN",
    "AIRCRAFT": "UNKNOWN",
    "WARNED": "Unknown",
}

# states where a positive longitude is real: foreign airports, Alaska past 180°
# and US islands in the Pacific
EAST_LONGITUDE_STATES = {"FN", "AK", "MP", "MH", "UM"}

PARTS = ["RAD", "WINDSHLD", "NOSE", "ENG1", "ENG2", "ENG3", "ENG4", "PROP",
         "WING_ROT", "FUSE", "LG", "TAIL", "LGHTS", "OTHER"]

COUNT_LEVELS = ["1", "2-10", "11-100", "More than 100"]

DATE_COLS = ["INCIDENT_DATE", "LUPDATE"]

INT_COLS = [
    "INDEX_NR", "INCIDENT_MONTH", "INCIDENT_YEAR", "AC_MASS", "NUM_ENGS",
    "NR_INJURIES", "NR_FATALITIES",
]

FLOAT_COLS = [
    "AIRPORT_LATITUDE", "AIRPORT_LONGITUDE", "HEIGHT", "SPEED", "DISTANCE", "AOS",
    "COST_REPAIRS", "COST_OTHER", "COST_REPAIRS_INFL_ADJ", "COST_OTHER_INFL_ADJ",
]

BOOL_COLS = [
    "INDICATED_DAMAGE", "INGESTED_OTHER", "OUT_OF_RANGE_SPECIES",
    *[f"{prefix}_{part}" for part in PARTS for prefix in ("STR", "DAM")],
    *[f"ING_ENG{i}" for i in range(1, 5)],
    "REMAINS_COLLECTED", "REMAINS_SENT",
]

CATEGORY_COLS = [
    "TIME_OF_DAY", "STATE", "FAAREGION", "AC_CLASS", "TYPE_ENG",
    "PHASE_OF_FLIGHT", "SKY", "PRECIPITATION", "DAMAGE_LEVEL",
    "EFFECT", "SIZE", "WARNED",
]


def _present(df: pd.DataFrame, columns) -> list[str]:
    return [col for col in columns if col in df.columns]


def clean_strings(df: pd.DataFrame) -> pd.DataFrame:
    """Trim spaces (AC_CLASS is 'A  ') and turn blank strings (TIME is '    ') into NaN."""
    df = df.copy()
    for col in df.select_dtypes("object").columns:
        df[col] = df[col].str.strip().replace("", pd.NA)
    return df


def replace_placeholders(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col, placeholder in PLACEHOLDERS.items():
        if col in df.columns:
            df[col] = df[col].mask(df[col] == placeholder)
    return df


def drop_constant_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop(columns=_present(df, CONSTANT_COLUMNS))


def drop_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """The same report sent twice gets a new INDEX_NR, so it is compared without it."""
    content = [col for col in df.columns if col != "INDEX_NR"]
    result = df.drop_duplicates(subset=content, keep="first")
    log.info("Dropped %d duplicated reports", len(df) - len(result))
    return result


def fix_coordinates(df: pd.DataFrame) -> pd.DataFrame:
    """Coordinates in other formats become NaN, a flipped longitude sign is fixed."""
    df = df.copy()
    lat = pd.to_numeric(df["AIRPORT_LATITUDE"], errors="coerce")
    lon = pd.to_numeric(df["AIRPORT_LONGITUDE"], errors="coerce")
    df["AIRPORT_LATITUDE"] = lat.where(lat.between(-90, 90))
    df["AIRPORT_LONGITUDE"] = lon.where(lon.between(-180, 180))

    flipped = (df["AIRPORT_LONGITUDE"] > 0) & ~df["STATE"].isin(EAST_LONGITUDE_STATES)
    df.loc[flipped, "AIRPORT_LONGITUDE"] *= -1
    log.info("Fixed the longitude sign in %d rows", flipped.sum())
    return df


def clean_precipitation(df: pd.DataFrame) -> pd.DataFrame:
    """'None, Rain' -> 'Rain': None can't go together with rain or snow."""
    df = df.copy()

    def drop_none(value):
        if pd.isna(value):
            return value
        items = [item.strip() for item in value.split(",")]
        if len(items) > 1:
            items = [item for item in items if item != "None"]
        return ", ".join(items)

    df["PRECIPITATION"] = df["PRECIPITATION"].map(drop_none)
    return df


def convert_types(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for col in _present(df, DATE_COLS):
        df[col] = pd.to_datetime(df[col], format="%Y-%m-%d", errors="coerce")

    for col in _present(df, INT_COLS):
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    for col in _present(df, FLOAT_COLS):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in _present(df, BOOL_COLS):
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("boolean")

    for col in _present(df, CATEGORY_COLS):
        df[col] = df[col].astype("category")

    # ranges like '2-10', not numbers, so they are ordered categories
    for col in _present(df, ["NUM_SEEN", "NUM_STRUCK"]):
        df[col] = pd.Categorical(df[col], categories=COUNT_LEVELS, ordered=True)

    return df


def fill_struck_flags(df: pd.DataFrame) -> pd.DataFrame:
    """A part can't be damaged or ingest something if it wasn't struck."""
    df = df.copy()
    fixed = 0
    for part in PARTS:
        struck_col = f"STR_{part}"
        if struck_col not in df.columns:
            continue
        struck = df[struck_col]
        hit = pd.Series(False, index=df.index)
        for col in _present(df, [f"DAM_{part}", f"ING_{part}"]):
            hit = hit | df[col].fillna(False)
        missing = hit & ~struck.fillna(False)
        fixed += int(missing.sum())
        df.loc[missing, struck_col] = True
    log.info("Set the struck flag for %d damaged parts", fixed)
    return df


def add_quality_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Flag rows where two fields contradict each other, it is not clear which one is wrong."""
    df = df.copy()
    hour = pd.to_datetime(df["TIME"], format="%H:%M", errors="coerce").dt.hour
    night_at_noon = (df["TIME_OF_DAY"] == "Night") & hour.between(10, 15)
    day_at_night = (df["TIME_OF_DAY"] == "Day") & hour.between(0, 4)
    df["FLAG_TIME_CONFLICT"] = (night_at_noon | day_at_night).astype("boolean")
    df["FLAG_UPDATED_BEFORE_INCIDENT"] = (df["LUPDATE"] < df["INCIDENT_DATE"]).astype("boolean")
    return df


def transform(df: pd.DataFrame) -> pd.DataFrame:
    result = (
        df.pipe(clean_strings)
        .pipe(replace_placeholders)
        .pipe(drop_constant_columns)
        .pipe(drop_duplicates)
        .pipe(fix_coordinates)
        .pipe(clean_precipitation)
        .pipe(convert_types)
        .pipe(fill_struck_flags)
        .pipe(add_quality_flags)
        .reset_index(drop=True)
    )
    log.info("Transformed: %d rows x %d columns", *result.shape)
    return result
