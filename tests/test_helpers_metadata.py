import datetime
import pandas as pd
import pytest

from hdhelpers import helpers_metadata_interface

def test_get_queried_interval(empty_series_with_attr):
    start, end = helpers_metadata_interface.get_queried_interval(empty_series_with_attr)
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

    assert start == datetime.datetime(2025,11,4,13,28, tzinfo=datetime.UTC)
    assert end == datetime.datetime(2025,11,7,13,28, tzinfo=datetime.UTC)

def test_get_queried_interval_not_given():
    start, end = helpers_metadata_interface.get_queried_interval(pd.Series())

    assert start == None
    assert end == None



def test_get_series_unit(empty_series_with_attr):
    unit = helpers_metadata_interface.get_series_unit(empty_series_with_attr)
    assert unit == "m³/s"


@pytest.mark.parametrize(
    ("attr", "output"),
    [
        pytest.param({ "by_metric": { "series": {"value_dimensions": {}}}}, None, id="value not given"),
        pytest.param({ "by_metric": { "series": {"value_dimensions": {"value": {"unit":None}}}}}, None, id="unit not given"),
        pytest.param({ "by_metric": { "series": {"value_dimensions": {"value": {"unit":"m/s"}}}}}, "m/s", id="given"),
    ],
)
def test_doctest_get_series_unit(attr, output):
    series = pd.Series()
    series.attrs = attr
    assert helpers_metadata_interface.get_series_unit(series) == output

def test_get_series_unit_no_attr():
    assert helpers_metadata_interface.get_series_unit(pd.Series()) == None



def test_get_series_name(empty_series_with_attr):
    unit = helpers_metadata_interface.get_series_name(empty_series_with_attr)
    assert unit == 'Wasserstand Ruhr Meschede'

@pytest.mark.parametrize(
    ("attr", "output"),
    [
        pytest.param({ "by_metric": { "series": {"value_dimensions": {"value": {"name": "value_name_of_series"}}}}}, "value_name_of_series", id="value name"),
        pytest.param({ "by_metric": { "series": {"metric": {"name": "name_of_series"}}}}, "name_of_series", id="name_of_series"),
        pytest.param({ "by_metric": { "series": {
            "metric": {"name": "name_of_series"},
            "value_dimensions": {"value": {"name": "value_name_of_series"}}}}}, "name_of_series", id="metric before value"),
    ],
)
def test_doctest_get_series_name(attr, output):
    series = pd.Series()
    series.attrs = attr
    assert helpers_metadata_interface.get_series_name(series) == output

def test_get_series_name_no_attr():
    assert helpers_metadata_interface.get_series_name(pd.Series()) == None



def test_get_display_name_series_name(empty_series_with_attr):
    display_name = helpers_metadata_interface.get_series_display_name(empty_series_with_attr)
    assert display_name == 'Wasserstand'

@pytest.mark.parametrize(
    ("attr", "output"),
    [
        pytest.param({ "by_metric": { "series": {"metric": {"display_name": "metric_display_name"}}}}, "metric_display_name", id="metric_display_name"),
        pytest.param({ "by_metric": { "series": {"value_dimensions": {"value": {"display_name": "value_display_name"}}}}}, "value_display_name", id="value_display_name"),
        pytest.param({ "by_metric": { "series": {"metric": {"display_name": "metric_display_name"},"value_dimensions": {"value": {"display_name": "value_display_name"}}}}}, "metric_display_name", id="metric before value"),
        pytest.param({ "by_metric": { "series": {"metric": {"name": "metric_display_name"}, "value_dimensions": {"value": {"display_name": "value_display_name"}}}}}, "value_display_name", id="value before metric name"),
        pytest.param({ "by_metric": { "series": {"metric": {"name": "metric_name"},"value_dimensions": {"value": {"name": "value_name"}}}}}, "metric_name", id="metric name before value name"),
    ],
)
def test_doctest_get_series_display_name(attr, output):
    series = pd.Series()
    series.attrs = attr
    assert helpers_metadata_interface.get_series_display_name(series) == output

def test_get_series_display_name_no_attr():
    assert helpers_metadata_interface.get_series_display_name(pd.Series()) == None


def test_get_short_display_name_series_name(empty_series_with_attr):
    display_name = helpers_metadata_interface.get_series_short_display_name(empty_series_with_attr)
    assert display_name == 'W'


@pytest.mark.parametrize(
    ("attr", "output"),
    [
        pytest.param({ "by_metric": { "series": {"metric": {"short_display_name": "short_display_name_of_series"}}}}, "short_display_name_of_series", id="metric_short_display_name"),
        pytest.param({ "by_metric": { "series": {"value_dimensions": {"value": {"short_display_name": "value_short_display_name"}}}}}, "value_short_display_name", id="value_short_display_name"),
        pytest.param({ "by_metric": { "series": {"metric": {"short_display_name": "metric_short_display_name"},"value_dimensions": {"value": {"short_display_name": "value_short_display_name"}}}}}, "metric_short_display_name", id="metric before value"),
        pytest.param({ "by_metric": { "series": {"metric": {"name": "metric_display_name"}, "value_dimensions": {"value": {"display_name": "value_display_name"}}}}}, "value_display_name", id="value display name before metric name"),
        pytest.param({ "by_metric": { "series": {"metric": {"name": "metric_name"},"value_dimensions": {"value": {"name": "value_name"}}}}}, "metric_name", id="metric name before value name"),
    ],
)
def test_doctest_get_series_short_display_name(attr, output):
    series = pd.Series()
    series.attrs = attr
    assert helpers_metadata_interface.get_series_short_display_name(series) == output

def test_get_series_display_name_no_attr():
    assert helpers_metadata_interface.get_series_short_display_name(pd.Series()) == None
