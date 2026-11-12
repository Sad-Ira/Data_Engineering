import pandas as pd

from etl import transform as t


def test_clean_strings_trims_and_blanks():
    df = pd.DataFrame({"AC_CLASS": ["A  ", "B"], "TIME": ["    ", "12:30"]})
    result = t.clean_strings(df)
    assert result["AC_CLASS"].tolist() == ["A", "B"]
    assert result["TIME"].isna().tolist() == [True, False]


def test_replace_placeholders():
    df = pd.DataFrame({"AIRPORT_ID": ["ZZZZ", "KDEN"], "WARNED": ["Unknown", "Yes"]})
    result = t.replace_placeholders(df)
    assert result["AIRPORT_ID"].isna().tolist() == [True, False]
    assert result["WARNED"].isna().tolist() == [True, False]


def test_drop_duplicates_ignores_index_nr():
    df = pd.DataFrame({"INDEX_NR": [1, 2, 3], "SPECIES": ["Gull", "Gull", "Hawk"]})
    assert t.drop_duplicates(df)["INDEX_NR"].tolist() == [1, 3]


def test_fix_coordinates():
    df = pd.DataFrame({
        "AIRPORT_LATITUDE": ["39.1", "49°09'05?N", "38.0", "51.9"],
        "AIRPORT_LONGITUDE": ["-104.6", "16°41'40?E", "97.2", "176.6"],
        "STATE": ["CO", "FN", "KS", "AK"],
    })
    result = t.fix_coordinates(df)
    assert result["AIRPORT_LATITUDE"].isna().tolist() == [False, True, False, False]
    # Kansas can't have a positive longitude, Alaska past 180° can
    assert result["AIRPORT_LONGITUDE"].tolist()[2:] == [-97.2, 176.6]


def test_clean_precipitation():
    df = pd.DataFrame({"PRECIPITATION": ["None, Rain", "Fog, Rain", "None", None]})
    result = t.clean_precipitation(df)["PRECIPITATION"]
    assert result.tolist()[:3] == ["Rain", "Fog, Rain", "None"]
    assert pd.isna(result.iloc[3])


def test_convert_types():
    df = pd.DataFrame({
        "INDEX_NR": ["1", "2"],
        "INCIDENT_DATE": ["2020-01-05", "bad"],
        "DAM_NOSE": [1, 0],
        "NUM_STRUCK": ["2-10", "1"],
    })
    result = t.convert_types(df)
    assert str(result["INDEX_NR"].dtype) == "Int64"
    assert pd.isna(result["INCIDENT_DATE"].iloc[1])
    assert str(result["DAM_NOSE"].dtype) == "boolean"
    assert result["NUM_STRUCK"].cat.ordered
    assert result["NUM_STRUCK"].iloc[0] > result["NUM_STRUCK"].iloc[1]


def test_fill_struck_flags():
    flags = {f"{p}_{part}": [False, False] for part in t.PARTS for p in ("STR", "DAM")}
    df = pd.DataFrame(flags, dtype="boolean")
    df.loc[0, "DAM_NOSE"] = True
    result = t.fill_struck_flags(df)
    assert result["STR_NOSE"].tolist() == [True, False]


def test_add_quality_flags():
    df = pd.DataFrame({
        "TIME": ["12:00", "2:00", "13:00"],
        "TIME_OF_DAY": ["Night", "Day", "Day"],
        "INCIDENT_DATE": pd.to_datetime(["2020-01-02"] * 3),
        "LUPDATE": pd.to_datetime(["2020-01-01", "2020-02-01", "2020-02-01"]),
    })
    result = t.add_quality_flags(df)
    assert result["FLAG_TIME_CONFLICT"].tolist() == [True, True, False]
    assert result["FLAG_UPDATED_BEFORE_INCIDENT"].tolist() == [True, False, False]
