"""The get_* functions, thin wrappers over the reading methods of the models"""

import datetime
from copy import deepcopy
from typing import Any

import numpy as np
import pandas as pd
import pytest

from hdhelpers.metadata import (
    Recording,
    attach_metadata,
    get_default_aggregation_methods,
    get_default_timezones,
    get_display_names,
    get_measurements,
    get_metric_info,
    get_names,
    get_queried_interval,
    get_recordings,
    get_series_default_aggregation_method,
    get_series_default_timezone,
    get_series_display_name,
    get_series_info,
    get_series_measurement,
    get_series_name,
    get_series_recording,
    get_series_short_display_name,
    get_series_unit,
    get_short_display_names,
    get_singlets_default_aggregation_method,
    get_singlets_default_timezone,
    get_singlets_display_names,
    get_singlets_info,
    get_singlets_metric_info,
    get_singlets_recording,
    get_singlets_short_display_names,
    get_singlets_units,
    get_units,
)

SIGNAL_ID = "7ab8c419-8745-4714-b588-57c0c772cc95"
REF_INTERVAL = {
    "ref_interval_start_timestamp": "2026-10-18T00:00:00Z",
    "ref_interval_end_timestamp": "2026-10-19T00:00:00Z",
    "ref_interval_type": "closed",
}


def value_dimension(**fields: Any) -> dict[str, Any]:
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


def metric(**fields: Any) -> dict[str, Any]:
    """Metric as the hetida platform sends it, with nulls for missing fields"""
    return {
        "id": SIGNAL_ID,
        "external_id": None,
        "name": "signal",
        "display_name": None,
        "description": None,
        "inherited": {},
        "comments": [],
        "value_dimensions": [value_dimension()],
        "default_aggregation_method": None,
    } | fields


def dataset_metadata(**fields: Any) -> dict[str, Any]:
    return {"metric_key": "id", "queried_metrics": []} | REF_INTERVAL | fields


# what the hetida platform sends for a timeseries of a SERIES read
platform_series_attrs = {
    "dataset_metadata": dataset_metadata(single_metric=SIGNAL_ID, queried_metrics=[SIGNAL_ID]),
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
    "dataset_metadata": dataset_metadata(queried_metrics=["level", "flow"]),
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

singletsframe_attrs = {
    "dataset_metadata": dataset_metadata(
        metric_key="external_id", single_metric="abc.temp", queried_metrics=["abc.temp"]
    ),
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


def series(attrs: dict[str, Any]) -> pd.Series:
    ser = pd.Series([1.0], index=pd.to_datetime(["2026-10-18T06:00:00Z"]))
    ser.attrs = deepcopy(attrs)
    return ser


def frame(attrs: dict[str, Any]) -> pd.DataFrame:
    df = pd.DataFrame()
    df.attrs = deepcopy(attrs)
    return df


def test_series_from_platform() -> None:
    platform_series = series(platform_series_attrs)

    assert get_series_unit(platform_series) == "m"
    assert get_series_measurement(platform_series) == "level"
    assert get_series_name(platform_series) == "Water-lvl-north"
    assert get_series_display_name(platform_series) == "Water-lvl-north"
    assert get_series_short_display_name(platform_series) == "Water-lvl-north"
    assert get_series_info(platform_series, "value_data_type") == "float"


def test_multitsframe_from_platform() -> None:
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
    assert get_metric_info(multitsframe, "name")["flow"] == "Pump-flow"


def test_each_field_is_looked_up_on_all_levels_before_the_next_field() -> None:
    attrs = {
        "dataset_metadata": dataset_metadata(),
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
        "value_dimensions_shared": [
            {"column": "state", "display_name": "shared display name"},
        ],
    }

    display_names = get_display_names(frame(attrs))

    assert display_names["a"]["value"] == "value name"
    assert display_names["a"]["state"] == "shared display name"
    assert display_names["b"]["value"] == "metric display name"
    assert display_names["c"]["value"] == "value display name"


def test_singletsframe() -> None:
    singletsframe = frame(singletsframe_attrs)

    assert get_singlets_units(singletsframe)["value"] == "°C"
    # only the value dimension "value" falls back to the metric
    assert get_singlets_display_names(singletsframe)["value"] == "ABC temp."
    assert get_singlets_display_names(singletsframe)["state"] == "measurement state"
    assert get_singlets_short_display_names(singletsframe)["state"] == "measurement state"
    assert get_singlets_info(singletsframe, "name")["state"] == "measurement state"
    assert get_singlets_info(singletsframe, "name")["unknown column"] is None
    assert get_singlets_metric_info(singletsframe, "name") == "ABC temperature"


def test_series_display_name_of_metric_wins_over_value_dimension_name() -> None:
    attrs = deepcopy(platform_series_attrs)
    attrs["metrics"][0]["display_name"] = "Level north"
    attrs["metrics"][0]["short_display_name"] = "north"

    assert get_series_display_name(series(attrs)) == "Level north"
    assert get_series_short_display_name(series(attrs)) == "north"


def test_series_display_name_does_not_fall_back_to_short_display_name() -> None:
    attrs = deepcopy(platform_series_attrs)
    attrs["metrics"][0]["value_dimensions"][0]["name"] = None
    attrs["metrics"][0]["short_display_name"] = "north"

    assert get_series_display_name(series(attrs)) == "Water-lvl-north"
    assert get_series_short_display_name(series(attrs)) == "north"


def test_metadata_not_following_the_conventions_gives_no_information() -> None:
    attrs = deepcopy(platform_series_attrs)
    # the single metric is another one than the metric present
    attrs["dataset_metadata"]["single_metric"] = "another signal"

    assert get_series_unit(series(attrs)) is None
    assert get_singlets_units(frame(attrs))["value"] is None
    assert get_singlets_metric_info(frame(attrs), "name") is None
    assert get_units(frame(attrs))[SIGNAL_ID]["value"] is None


@pytest.mark.parametrize(
    "attrs", [{}, {"dataset_metadata": {"metric_key": "id"}}, {"metrics": None}]
)
def test_without_metadata(attrs: dict[str, Any]) -> None:
    """Components should not require metadata, so missing metadata must not raise"""
    assert get_metric_info(frame(attrs), "name")["any metric"] is None
    assert get_series_unit(series(attrs)) is None
    assert get_singlets_units(frame(attrs))["value"] is None
    assert get_default_timezones(frame(attrs))["any metric"] is None
    assert get_recordings(frame(attrs))["any metric"] == Recording()
    assert get_series_default_aggregation_method(series(attrs)) == "MEAN"
    assert get_queried_interval(series(attrs)) == (None, None)


def multitsframe_with_data(attrs: dict[str, Any]) -> pd.DataFrame:
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-10-18T06:00", periods=2, freq="h", tz="UTC"),
            "metric": ["level", "flow"],
            "value": np.arange(2.0),
        }
    )
    df.attrs = deepcopy(attrs)
    return df


def test_attached_metadata_of_another_data_type() -> None:
    """E.g. a Series taken from a MultiTSFrame, whose metadata it carries"""
    attrs = deepcopy(platform_multitsframe_attrs)
    attrs["dataset_metadata"]["default_timezone"] = "UTC"
    attrs["metrics"][0]["default_timezone"] = "Asia/Tokyo"
    multitsframe = multitsframe_with_data(attrs)
    attach_metadata(multitsframe)
    values = multitsframe["value"]

    # several metrics, none of which is the single one
    assert get_series_name(values) is None
    assert get_series_default_timezone(values) == "UTC"

    one_metric = multitsframe[multitsframe["metric"] == "level"]
    assert get_units(one_metric)["level"]["value"] == "m"


def test_attached_singletsframe_metadata_on_a_series() -> None:
    singletsframe = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-10-18T06:00", periods=2, freq="h", tz="UTC"),
            "value": [1.0, 2.0],
            "state": ["ok", "ok"],
        }
    )
    singletsframe.attrs = deepcopy(singletsframe_attrs)
    attach_metadata(singletsframe)

    assert get_series_unit(singletsframe["value"]) == "°C"
    assert get_series_display_name(singletsframe["value"]) == "ABC temp."


@pytest.mark.parametrize("include_inherited", [False, True])
def test_short_display_names_of_metrics_resolved_by_different_fields(
    include_inherited: bool,
) -> None:
    """Each metric gets its information from the first field providing it, independently"""
    attrs = {
        "dataset_metadata": dataset_metadata(),
        "metrics": [
            metric(
                id="a",
                short_display_name="a short",
                value_dimensions=[value_dimension(), value_dimension(column="state")],
            ),
            metric(id="b", display_name="b display", name="b name"),
            metric(id="c", name="c name"),
        ],
        "value_dimensions_shared": [{"column": "state", "name": "shared state"}],
    }

    short_display_names = get_short_display_names(frame(attrs), include_inherited=include_inherited)

    assert short_display_names["a"]["value"] == "a short"
    assert short_display_names["a"]["state"] == "shared state"
    assert short_display_names["b"]["value"] == "b display"
    assert short_display_names["c"]["value"] == "c name"
    assert short_display_names["c"]["state"] == "shared state"


def test_inherited_properties() -> None:
    attrs = deepcopy(platform_multitsframe_attrs)
    attrs["metrics"][1]["inherited"] = {"unit": "m³/h", "site": "north"}

    assert get_units(frame(attrs))["flow"]["value"] is None
    assert get_units(frame(attrs), include_inherited=True)["flow"]["value"] == "m³/h"
    assert get_metric_info(frame(attrs), "site")["flow"] == "north"
    assert get_metric_info(frame(attrs), "site", include_inherited=False)["flow"] is None


def test_default_timezones_fall_back_to_the_dataset_metadata() -> None:
    attrs = {
        "dataset_metadata": dataset_metadata(
            metric_key="external_id", default_timezone="Europe/Berlin"
        ),
        "metrics": [
            metric(external_id="new_york", default_timezone="America/New_York"),
            metric(id="2", external_id="fixed_offset", default_timezone="+02:00"),
            metric(id="3", external_id="without"),
        ],
    }

    timezones = get_default_timezones(frame(attrs))

    assert timezones == {
        "new_york": "America/New_York",
        "fixed_offset": "+02:00",
        "without": "Europe/Berlin",
    }
    assert timezones["metric without metadata"] == "Europe/Berlin"


def test_default_timezone_of_single_metric() -> None:
    attrs = deepcopy(platform_series_attrs)
    attrs["dataset_metadata"]["default_timezone"] = "Europe/Berlin"

    assert get_series_default_timezone(series(attrs)) == "Europe/Berlin"
    attrs["metrics"][0]["default_timezone"] = "America/New_York"
    assert get_series_default_timezone(series(attrs)) == "America/New_York"
    assert get_singlets_default_timezone(frame(attrs)) == "America/New_York"


def test_recordings_fall_back_to_the_frequency_of_the_dataset_as_a_whole() -> None:
    attrs = {
        "dataset_metadata": dataset_metadata(
            metric_key="external_id",
            ref_data_frequency="1h",
            ref_data_frequency_offset="30min",
            ref_data_frequency_timezone="Europe/Berlin",
        ),
        "metrics": [
            metric(
                id="1",
                external_id="own_frequency",
                recording_mode="periodic",
                data_frequency="15min",
                recording_aggregation_method="MEAN",
            ),
            metric(id="2", external_id="dataset_frequency", recording_mode="on_change"),
        ],
    }
    dataset_frequency = {
        "data_frequency": "1h",
        "data_frequency_offset": "30min",
        "data_frequency_timezone": "Europe/Berlin",
    }

    recordings = get_recordings(frame(attrs))

    assert recordings == {
        "own_frequency": Recording(
            recording_mode="periodic", data_frequency="15min", recording_aggregation_method="MEAN"
        ),
        "dataset_frequency": Recording(recording_mode="on_change", **dataset_frequency),
    }
    assert recordings["metric without metadata"] == Recording(**dataset_frequency)


def test_single_metric_recording() -> None:
    attrs = deepcopy(platform_series_attrs)
    attrs["metrics"][0] |= {"recording_mode": "periodic", "data_frequency": "15min"}

    expected = Recording(recording_mode="periodic", data_frequency="15min")
    assert get_series_recording(series(attrs)) == expected
    assert get_singlets_recording(frame(attrs)) == expected


def test_default_aggregation_methods() -> None:
    attrs = deepcopy(platform_multitsframe_attrs)
    attrs["metrics"][0]["default_aggregation_method"] = "SUM"
    attrs["metrics"][1]["value_dimensions"][0]["value_data_type"] = "boolean"

    methods = get_default_aggregation_methods(frame(attrs))

    assert methods == {"level": "SUM", "flow": "LAST"}
    assert methods["metric without metadata"] == "MEAN"
    assert get_series_default_aggregation_method(series(platform_series_attrs)) == "MEAN"
    assert get_singlets_default_aggregation_method(frame(platform_series_attrs)) == "MEAN"


def test_queried_interval() -> None:
    assert get_queried_interval(series(platform_series_attrs)) == (
        datetime.datetime(2026, 10, 18, tzinfo=datetime.UTC),
        datetime.datetime(2026, 10, 19, tzinfo=datetime.UTC),
    )


def test_many_metrics() -> None:
    attrs = {
        "dataset_metadata": dataset_metadata(),
        "metrics": [
            metric(
                id=f"m{i}",
                name=f"Metric {i}",
                inherited={"site": "north"},
                value_dimensions=[value_dimension(name=f"Metric {i}", unit="m")],
            )
            for i in range(1000)
        ],
    }
    multitsframe = frame(attrs)

    assert get_short_display_names(multitsframe)["m999"]["value"] == "Metric 999"
    assert get_units(multitsframe)["m0"]["value"] == "m"
    assert get_metric_info(multitsframe, "unit")["m500"] == "m"
    assert get_metric_info(multitsframe, "site")["m1"] == "north"


@pytest.mark.parametrize(
    ("function", "data"),
    [
        (get_units, pd.Series(dtype=float)),
        (get_default_timezones, pd.Series(dtype=float)),
        (get_singlets_units, pd.Series(dtype=float)),
        (get_series_unit, pd.DataFrame()),
        (get_series_recording, pd.DataFrame()),
        (get_queried_interval, {}),
    ],
)
def test_wrong_input_types_raise(function: Any, data: Any) -> None:
    with pytest.raises(TypeError):
        function(data)
