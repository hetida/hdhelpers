import json
import pandas as pd
import pytest

@pytest.fixture(scope="function")
def empty_mts_with_old_attr() -> pd.DataFrame:
    with open("tests/data/old_mts_attrs.json", "r") as file:
        metadata_for_mts = json.load(file)

    empty_mts = pd.DataFrame()
    empty_mts.attrs = metadata_for_mts
    return empty_mts


@pytest.fixture(scope="function")
def empty_mts_with_attr() -> pd.DataFrame:
    with open("tests/data/mts_attrs.json", "r") as file:
        metadata_for_mts = json.load(file)

    empty_mts = pd.DataFrame()
    empty_mts.attrs = metadata_for_mts
    return empty_mts

@pytest.fixture(scope="function")
def empty_mts_with_old_attr_real() -> pd.DataFrame:
    with open("tests/data/mts_attrs_old_real.json", "r") as file:
        metadata_for_mts = json.load(file)

    empty_mts = pd.DataFrame()
    empty_mts.attrs = metadata_for_mts
    return empty_mts

@pytest.fixture(scope="function")
def empty_series_with_old_attr_real() -> pd.Series:
    with open("tests/data/series_attrs_old_real.json", "r") as file:
        metadata_for_series = json.load(file)

    empty_series = pd.Series()
    empty_series.attrs = metadata_for_series
    return empty_series

@pytest.fixture(scope="function")
def empty_series_with_old_attr() -> pd.Series:
    with open("tests/data/old_series_attrs.json", "r") as file:
        metadata_for_series = json.load(file)

    empty_series = pd.Series()
    empty_series.attrs = metadata_for_series
    return empty_series

@pytest.fixture(scope="function")
def empty_series_with_attr() -> pd.Series:
    with open("tests/data/series_attrs.json", "r") as file:
        metadata_for_series = json.load(file)

    empty_series = pd.Series()
    empty_series.attrs = metadata_for_series
    return empty_series
