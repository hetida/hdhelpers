"""Recording of the metrics and their default aggregation methods"""

import pandas as pd
import pytest

from hdhelpers.metadata import (
    Recording,
    get_default_aggregation_methods,
    get_recordings,
    get_series_default_aggregation_method,
    get_series_recording,
    get_singlets_default_aggregation_method,
    get_singlets_recording,
)


def frame(attrs):
    df = pd.DataFrame()
    df.attrs = attrs
    return df


def series(attrs):
    ser = pd.Series(dtype=float)
    ser.attrs = attrs
    return ser


def value_data_type(data_type):
    return [{"column": "value", "unit": None, "measurement": None, "value_data_type": data_type}]


multitsframe_attrs = {
    "dataset_metadata": {
        "metric_key": "external_id",
        "ref_data_frequency": "1h",
        "ref_data_frequency_offset": "30min",
        "ref_data_frequency_timezone": "Europe/Berlin",
    },
    "metrics": [
        {
            "external_id": "own_frequency",
            "recording_mode": "periodic",
            "data_frequency": "15min",
            "recording_aggregation_method": "MEAN",
        },
        # the offset and time zone of the metric only apply together with its frequency
        {
            "external_id": "without_frequency",
            "recording_mode": "on_change",
            "data_frequency_offset": "5min",
            "data_frequency_timezone": "UTC",
        },
        {"external_id": "null_frequency", "data_frequency": None},
        {"external_id": "no_string", "data_frequency": 15, "recording_mode": 1},
    ],
}

dataset_frequency = {
    "data_frequency": "1h",
    "data_frequency_offset": "30min",
    "data_frequency_timezone": "Europe/Berlin",
}


def test_recordings_fall_back_to_the_frequency_of_the_dataset_as_a_whole():
    recordings = get_recordings(frame(multitsframe_attrs))

    assert recordings == {
        "own_frequency": Recording(
            recording_mode="periodic",
            data_frequency="15min",
            recording_aggregation_method="MEAN",
        ),
        "without_frequency": Recording(recording_mode="on_change", **dataset_frequency),
        "null_frequency": Recording(**dataset_frequency),
        "no_string": Recording(**dataset_frequency),
    }
    assert recordings["metric without metadata"] == Recording(**dataset_frequency)


@pytest.mark.parametrize(
    "attrs",
    [
        {},
        {"metrics": "no list"},
        # an older metadata structure, whose metrics are not considered
        {"dataset_metadata": {}, "metrics": {"a": {"data_frequency": "1h"}}},
    ],
)
def test_recordings_without_metric_metadata(attrs):
    recordings = get_recordings(frame(attrs))

    assert recordings == {}
    assert recordings["a"] == Recording()


def test_series_recording():
    attrs = {
        "dataset_metadata": {"single_metric": "b", "ref_data_frequency": "1D"},
        "metrics": [{"id": "b", "recording_mode": "periodic", "data_frequency_offset": "1h"}],
    }

    assert get_series_recording(series(attrs)) == Recording(
        recording_mode="periodic", data_frequency="1D"
    )


def test_singlets_recording_falls_back_to_the_dataset_if_the_metric_is_not_found():
    attrs = {
        "dataset_metadata": {"single_metric": "missing", "ref_data_frequency": "5min"},
        "metrics": [{"id": "a", "data_frequency": "1h"}, {"id": "b"}],
    }

    assert get_singlets_recording(frame(attrs)) == Recording(data_frequency="5min")


def test_recording_functions_check_their_input():
    with pytest.raises(TypeError):
        get_recordings(series({}))
    with pytest.raises(TypeError):
        get_series_recording(frame({}))
    with pytest.raises(TypeError):
        get_singlets_recording(series({}))


def test_default_aggregation_methods():
    attrs = {
        "dataset_metadata": {"metric_key": "id"},
        "metrics": [
            {"id": "avg", "default_aggregation_method": "AVG"},
            {"id": "sum", "default_aggregation_method": "SUM"},
            {"id": "float", "value_dimensions": value_data_type("float")},
            {"id": "integer", "value_dimensions": value_data_type("integer")},
            {"id": "boolean", "value_dimensions": value_data_type("boolean")},
            {"id": "string", "value_dimensions": value_data_type("string")},
            # the method of the metric takes precedence over the default of its data type
            {
                "id": "boolean_max",
                "default_aggregation_method": "MAX",
                "value_dimensions": value_data_type("boolean"),
            },
            {"id": "null", "default_aggregation_method": None},
            {"id": "shared_data_type", "value_dimensions": []},
        ],
        "value_dimensions_shared": [{"column": "value", "value_data_type": "string"}],
    }

    methods = get_default_aggregation_methods(frame(attrs))

    assert methods == {
        "avg": "MEAN",
        "sum": "SUM",
        "float": "MEAN",
        "integer": "MEAN",
        "boolean": "LAST",
        "string": "LAST",
        "boolean_max": "MAX",
        # the value data type of the shared value dimension "value" applies
        "null": "LAST",
        "shared_data_type": "LAST",
    }
    assert methods["metric without metadata"] == "MEAN"


@pytest.mark.parametrize(
    ("attrs", "method"),
    [
        ({}, "MEAN"),
        ({"metrics": {"a": {"default_aggregation_method": "SUM"}}}, "MEAN"),
        (
            {
                "dataset_metadata": {"single_metric": "a"},
                "metrics": [{"id": "a", "value_dimensions": value_data_type("boolean")}],
            },
            "LAST",
        ),
        ({"metrics": [{"id": "a", "default_aggregation_method": "AVG"}]}, "MEAN"),
    ],
)
def test_single_metric_default_aggregation_method(attrs, method):
    assert get_series_default_aggregation_method(series(attrs)) == method
    assert get_singlets_default_aggregation_method(frame(attrs)) == method
