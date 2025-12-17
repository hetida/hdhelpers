import datetime
import json
import pandas as pd

from hdhelpers import helpers_metadata_interface

def test_get_queried_interval():
    with open("tests/data/series_attrs.json", "r") as file:
        metadata_for_series = json.load(file)

    empty_series = pd.Series()
    empty_series.attrs = metadata_for_series

    start, end = helpers_metadata_interface.get_queried_interval(empty_series)
    assert start == datetime.datetime(2025, 11, 5, 13, 28, tzinfo=datetime.UTC)
    assert end == datetime.datetime(2025, 11, 6, 13, 28, tzinfo=datetime.UTC)


def test_doctest_get_queried_interval():
    attr = {
            "dataset_metadata": {
            "ref_interval_start_timestamp": "2025-11-04T13:28:00Z",
            "ref_interval_end_timestamp": "2025-11-07T13:28:00Z"
        }
    }
    series = pd.Series()
    series.attrs = attr
    start, end = helpers_metadata_interface.get_queried_interval(series)

    assert start == datetime.datetime(2025,11,4,31,28, tzinfo=datetime.UTC)
    assert end == datetime.datetime(2025,11,7,31,28, tzinfo=datetime.UTC)
