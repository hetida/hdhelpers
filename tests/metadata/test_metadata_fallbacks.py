"""Fallbacks for metadata following the current metadata convention

Metadata providers like the hetida platform send fields without value explicitly as null.
These count as missing: The accessors fall back to the next level or field as if the field
was not provided at all.
"""

from copy import deepcopy

import pandas as pd
import pytest

from hdhelpers.metadata import (
    get_display_names,
    get_measurements,
    get_metric_info,
    get_names,
    get_series_display_name,
    get_series_measurement,
    get_series_name,
    get_series_short_display_name,
    get_series_unit,
    get_short_display_names,
    get_singlets_display_names,
    get_singlets_short_display_names,
    get_singlets_units,
    get_units,
)

SIGNAL_ID = "7ab8c419-8745-4714-b588-57c0c772cc95"


def value_dimension(**fields):
    """Value dimension "value" as the hetida platform sends it, with nulls for missing fields"""
    return {
        "column": "value",
        "name": None,
        "display_name": None,
        "short_display_name": None,
        "description": None,
        "unit": None,
        "measurement": None,
        "value_data_type": "float",
    } | fields


def metric(**fields):
    """Metric as the hetida platform sends it, with nulls for missing fields"""
    return {
        "id": SIGNAL_ID,
        "external_id": None,
        "name": None,
        "display_name": None,
        "description": None,
        "inherited": {},
        "comments": [],
        "value_dimensions": [value_dimension()],
        "default_aggregation_method": None,
    } | fields


# what the hetida platform sends for a timeseries of a SERIES read
platform_series_attrs = {
    "dataset_metadata": {
        "metric_key": "id",
        "single_metric": SIGNAL_ID,
        "queried_metrics": [SIGNAL_ID],
        "ref_interval_start_timestamp": "2026-10-18T00:00:00Z",
        "ref_interval_end_timestamp": "2026-10-19T00:00:00Z",
        "ref_interval_type": "closed",
    },
    "metrics": [
        metric(
            external_id="water.north.level",
            name="Water-lvl-north",
            value_dimensions=[
                value_dimension(name="Water-lvl-north", unit="m", measurement="level")
            ],
            default_aggregation_method="AVG",
        )
    ],
}

# what the hetida platform sends for a MULTITSFRAME read of a signal group: display_name of
# a metric is the display name configured for the member of the group
platform_multitsframe_attrs = {
    "dataset_metadata": {"metric_key": "id", "queried_metrics": ["level", "flow"]},
    "metrics": [
        metric(
            id="level",
            name="Water-lvl-north",
            value_dimensions=[value_dimension(name="Water-lvl-north", unit="m")],
        ),
        metric(
            id="flow",
            name="Pump-flow",
            display_name="Flow pump 1",
            value_dimensions=[value_dimension(name="Pump-flow")],
        ),
    ],
}


def series(attrs):
    ser = pd.Series([1.0], index=pd.to_datetime(["2026-10-18T06:00:00Z"]))
    ser.attrs = deepcopy(attrs)
    return ser


def frame(attrs):
    df = pd.DataFrame()
    df.attrs = deepcopy(attrs)
    return df


def test_series_from_platform():
    platform_series = series(platform_series_attrs)

    assert get_series_unit(platform_series) == "m"
    assert get_series_measurement(platform_series) == "level"
    assert get_series_name(platform_series) == "Water-lvl-north"
    assert get_series_display_name(platform_series) == "Water-lvl-north"
    assert get_series_short_display_name(platform_series) == "Water-lvl-north"


def test_multitsframe_from_platform():
    multitsframe = frame(platform_multitsframe_attrs)

    assert get_units(multitsframe)["level"]["value"] == "m"
    assert get_units(multitsframe)["flow"]["value"] is None
    assert get_names(multitsframe)["flow"]["value"] == "Pump-flow"
    assert get_measurements(multitsframe)["level"]["value"] is None
    # a null display name falls back to the name
    assert get_display_names(multitsframe)["level"]["value"] == "Water-lvl-north"
    assert get_short_display_names(multitsframe)["level"]["value"] == "Water-lvl-north"
    # the display name of the metric wins over the name of its value dimension
    assert get_display_names(multitsframe)["flow"]["value"] == "Flow pump 1"
    assert get_short_display_names(multitsframe)["flow"]["value"] == "Flow pump 1"


def test_each_field_is_looked_up_on_all_levels_before_the_next_field():
    attrs = {
        "metrics": [
            metric(
                id="a",
                name="metric name",
                value_dimensions=[
                    value_dimension(name="value name"),
                    value_dimension(column="state", name="state name"),
                ],
            ),
            metric(id="b", name="metric name", display_name="metric display name"),
            metric(
                id="c",
                display_name="metric display name",
                value_dimensions=[value_dimension(display_name="value display name")],
            ),
        ],
        "value_dimensions_shared": [{"column": "state", "display_name": "shared display name"}],
    }

    display_names = get_display_names(frame(attrs))

    assert display_names["a"]["value"] == "value name"
    assert display_names["a"]["state"] == "shared display name"
    assert display_names["b"]["value"] == "metric display name"
    assert display_names["c"]["value"] == "value display name"


def test_singletsframe_display_names():
    attrs = {
        "dataset_metadata": {"single_metric": "abc.temp", "metric_key": "external_id"},
        "metrics": [
            metric(
                external_id="abc.temp",
                name="ABC temperature",
                display_name="ABC temp.",
                value_dimensions=[
                    value_dimension(name="temperature", unit="°C"),
                    value_dimension(column="state", name="measurement state"),
                ],
            )
        ],
    }
    singletsframe = frame(attrs)

    assert get_singlets_units(singletsframe)["value"] == "°C"
    # only the value dimension "value" falls back to the metric
    assert get_singlets_display_names(singletsframe)["value"] == "ABC temp."
    assert get_singlets_display_names(singletsframe)["state"] == "measurement state"
    assert get_singlets_short_display_names(singletsframe)["state"] == "measurement state"


def test_series_display_name_of_metric_wins_over_value_dimension_name():
    attrs = deepcopy(platform_series_attrs)
    attrs["metrics"][0]["display_name"] = "Level north"
    attrs["metrics"][0]["short_display_name"] = "north"

    assert get_series_display_name(series(attrs)) == "Level north"
    assert get_series_short_display_name(series(attrs)) == "north"


def test_series_without_single_metric_uses_its_only_metric():
    attrs = deepcopy(platform_series_attrs)
    del attrs["dataset_metadata"]["single_metric"]

    assert get_series_unit(series(attrs)) == "m"
    assert get_series_display_name(series(attrs)) == "Water-lvl-north"


@pytest.mark.parametrize(
    "attrs",
    [{}, {"dataset_metadata": {"metric_key": "id"}}, {"metrics": None}],
)
def test_metric_info_without_metric_metadata(attrs):
    """Components should not require metadata, so missing metric metadata must not raise"""
    assert get_metric_info(frame(attrs), "name")["any metric"] is None


def test_metric_info_from_platform():
    multitsframe = frame(platform_multitsframe_attrs)
    multitsframe.attrs["metrics"][0]["default_aggregation_method"] = "SUM"

    aggregation_methods = get_metric_info(multitsframe, "default_aggregation_method")

    assert aggregation_methods["level"] == "SUM"
    assert aggregation_methods["flow"] is None
