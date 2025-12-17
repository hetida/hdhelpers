import json
import pandas as pd
import pytest

@pytest.fixture(scope="session")
def empty_series_with_attr() -> pd.Series:
    with open("tests/data/series_attrs.json", "r") as file:
        metadata_for_series = json.load(file)

    empty_series = pd.Series()
    empty_series.attrs = metadata_for_series
    return empty_series
