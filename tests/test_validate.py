import pandas as pd
import pytest

from etl.validate import ValidationError, validate


def make_clean() -> pd.DataFrame:
    return pd.DataFrame({
        "INDEX_NR": pd.array([1, 2], dtype="Int64"),
        "INCIDENT_DATE": pd.to_datetime(["2020-01-05", "2021-07-10"]),
        "INCIDENT_MONTH": pd.array([1, 7], dtype="Int64"),
        "INCIDENT_YEAR": pd.array([2020, 2021], dtype="Int64"),
        "AIRPORT_ID": ["KDEN", None],
        "SPECIES": ["Gull", "Hawk"],
        "NUM_STRUCK": ["1", "2-10"],
        "INDICATED_DAMAGE": pd.array([False, True], dtype="boolean"),
        "HEIGHT": [0.0, 1500.0],
    })


def test_clean_data_passes():
    df = make_clean()
    assert validate(df) is df


def test_problems_are_collected_together():
    df = make_clean()
    df.loc[1, "INDEX_NR"] = 1
    df.loc[0, "HEIGHT"] = -5
    df.loc[0, "SPECIES"] = "Gull "
    with pytest.raises(ValidationError) as error:
        validate(df)
    assert len(error.value.problems) == 3


def test_missing_column_and_wrong_month():
    df = make_clean().drop(columns="SPECIES")
    df.loc[0, "INCIDENT_MONTH"] = 2
    with pytest.raises(ValidationError) as error:
        validate(df)
    text = str(error.value)
    assert "SPECIES" in text and "don't match the date" in text
