"""Validate: check the transformed data before it leaves the pipeline.

All problems are collected and reported together, so one run shows everything to fix.
"""

import logging
from datetime import date

import pandas as pd
from pandas.api import types

from etl.transform import BOOL_COLS, CONSTANT_COLUMNS, PARTS

log = logging.getLogger(__name__)

REQUIRED_COLUMNS = [
    "INDEX_NR", "INCIDENT_DATE", "INCIDENT_MONTH", "INCIDENT_YEAR",
    "AIRPORT_ID", "SPECIES", "NUM_STRUCK", "INDICATED_DAMAGE",
]

# The EDA observed maxima of 32,000 ft and 541 kt. The validation limits
# allow headroom above those observations while still catching extreme values.
RANGES = {
    "AIRPORT_LATITUDE": (-90, 90),
    "AIRPORT_LONGITUDE": (-180, 180),
    "INCIDENT_MONTH": (1, 12),
    "INCIDENT_YEAR": (1990, date.today().year),
    "HEIGHT": (0, 50_000),
    "SPEED": (0, 600),
    "DISTANCE": (0, None),
    "AOS": (0, None),
    "COST_REPAIRS": (0, None),
    "COST_OTHER": (0, None),
    "NR_INJURIES": (0, None),
    "NR_FATALITIES": (0, None),
}


class ValidationError(Exception):
    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("Validation failed:\n- " + "\n- ".join(problems))


def check_structure(df: pd.DataFrame) -> list[str]:
    problems = []
    if df.empty:
        problems.append("the dataset is empty")
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        problems.append(f"missing columns: {missing}")
    constant = [col for col in CONSTANT_COLUMNS if col in df.columns]
    if constant:
        problems.append(f"constant columns are not dropped: {constant}")
    return problems


def check_types(df: pd.DataFrame) -> list[str]:
    problems = []
    for col in ["INCIDENT_DATE", "LUPDATE"]:
        if col in df.columns and not types.is_datetime64_any_dtype(df[col]):
            problems.append(f"{col} is {df[col].dtype}, expected datetime")
    for col in ["INDEX_NR", "INCIDENT_MONTH", "INCIDENT_YEAR"]:
        if col in df.columns and not types.is_integer_dtype(df[col]):
            problems.append(f"{col} is {df[col].dtype}, expected integer")
    for col in BOOL_COLS:
        if col in df.columns and not types.is_bool_dtype(df[col]):
            problems.append(f"{col} is {df[col].dtype}, expected boolean")
    return problems


def check_keys(df: pd.DataFrame) -> list[str]:
    problems = []
    if "INDEX_NR" in df.columns:
        if df["INDEX_NR"].isna().any():
            problems.append("INDEX_NR has empty values")
        if not df["INDEX_NR"].is_unique:
            problems.append("INDEX_NR is not unique")
    content = [col for col in df.columns if col != "INDEX_NR"]
    duplicates = int(df.duplicated(subset=content).sum())
    if duplicates:
        problems.append(f"{duplicates} duplicated reports")
    return problems


def check_ranges(df: pd.DataFrame) -> list[str]:
    problems = []
    for col, (low, high) in RANGES.items():
        if col not in df.columns:
            continue
        values = df[col].dropna()
        bad = pd.Series(False, index=values.index)
        if low is not None:
            bad |= values < low
        if high is not None:
            bad |= values > high
        if bad.any():
            problems.append(f"{col}: {int(bad.sum())} values out of [{low}, {high}]")
    return problems


def check_consistency(df: pd.DataFrame) -> list[str]:
    problems = []
    if {"INCIDENT_DATE", "INCIDENT_MONTH", "INCIDENT_YEAR"} <= set(df.columns):
        dates = df["INCIDENT_DATE"]
        ok = dates.notna()
        wrong = (dates[ok].dt.month != df.loc[ok, "INCIDENT_MONTH"]) | (
            dates[ok].dt.year != df.loc[ok, "INCIDENT_YEAR"]
        )
        if wrong.any():
            problems.append(f"{int(wrong.sum())} rows where month or year don't match the date")

    for part in PARTS:
        struck, damaged = f"STR_{part}", f"DAM_{part}"
        if {struck, damaged} <= set(df.columns):
            wrong = df[damaged].fillna(False) & ~df[struck].fillna(False)
            if wrong.any():
                problems.append(f"{int(wrong.sum())} rows with {damaged} but not {struck}")

    if "PRECIPITATION" in df.columns:
        mixed = df["PRECIPITATION"].astype("string").str.contains("None,|, None", na=False)
        if mixed.any():
            problems.append(f"{int(mixed.sum())} rows with None mixed with other precipitation")
    return problems


def check_strings(df: pd.DataFrame) -> list[str]:
    problems = []
    for col in df.columns:
        if not (types.is_object_dtype(df[col]) or isinstance(df[col].dtype, pd.CategoricalDtype)):
            continue
        values = df[col].dropna().astype("string")
        if values.empty:
            continue
        if (values != values.str.strip()).any():
            problems.append(f"{col} has values with extra spaces")
        if values.eq("").any():
            problems.append(f"{col} has blank strings")
    return problems


CHECKS = [check_structure, check_types, check_keys, check_ranges, check_consistency, check_strings]


def validate(df: pd.DataFrame) -> pd.DataFrame:
    """Return the same DataFrame if every check passes, otherwise raise ValidationError."""
    problems = [problem for check in CHECKS for problem in check(df)]
    if problems:
        raise ValidationError(problems)
    log.info("Validation passed: %d checks on %d rows", len(CHECKS), len(df))
    return df
