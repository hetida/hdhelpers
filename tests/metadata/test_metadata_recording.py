"""Recording of the metrics, their default aggregation methods and the recording intervals"""

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
    recording_grid,
    recording_interval_starts,
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


def utc(*timestamps):
    return pd.DatetimeIndex(pd.to_datetime(list(timestamps), utc=True))


def local(index, timezone="Europe/Berlin"):
    return [timestamp.isoformat() for timestamp in index.tz_convert(timezone)]


@pytest.mark.parametrize(
    ("recording", "timestamps", "expected_starts"),
    [
        # multiples since 1970-01-01T00:00:00Z plus offset
        (
            Recording(data_frequency="15min", data_frequency_offset="5min"),
            ["2026-01-01T00:04:59Z", "2026-01-01T00:05:00Z", "2026-01-01T00:19:59Z"],
            ["2025-12-31T23:50:00Z", "2026-01-01T00:05:00Z", "2026-01-01T00:05:00Z"],
        ),
        (
            Recording(data_frequency="1D"),
            ["2026-03-29T23:59:00Z"],
            ["2026-03-29T00:00:00Z"],
        ),
        (
            Recording(data_frequency="P2D"),
            ["2026-01-04T12:00:00Z"],
            ["2026-01-03T00:00:00Z"],
        ),
    ],
)
def test_recording_interval_starts_in_utc(recording, timestamps, expected_starts):
    assert recording_interval_starts(utc(*timestamps), recording).equals(utc(*expected_starts))


def test_recording_intervals_restart_at_local_midnight():
    # the clocks are put forward at 02:00 local time on 2026-03-29, so the day has 23 hours
    recording = Recording(data_frequency="2h", data_frequency_timezone="Europe/Berlin")

    grid = recording_grid("2026-03-28T20:00:00Z", "2026-03-29T23:00:00Z", recording)

    assert local(grid) == [
        "2026-03-28T22:00:00+01:00",
        "2026-03-29T00:00:00+01:00",
        # 2 hours after midnight in elapsed time
        "2026-03-29T03:00:00+02:00",
        "2026-03-29T05:00:00+02:00",
        "2026-03-29T07:00:00+02:00",
        "2026-03-29T09:00:00+02:00",
        "2026-03-29T11:00:00+02:00",
        "2026-03-29T13:00:00+02:00",
        "2026-03-29T15:00:00+02:00",
        "2026-03-29T17:00:00+02:00",
        "2026-03-29T19:00:00+02:00",
        "2026-03-29T21:00:00+02:00",
        # the last interval of the day lasts 1 hour, until the next local midnight
        "2026-03-29T23:00:00+02:00",
        "2026-03-30T00:00:00+02:00",
    ]
    starts = recording_interval_starts(
        utc("2026-03-29T21:30:00Z", "2026-03-29T22:00:00Z"), recording
    )
    assert local(starts) == ["2026-03-29T23:00:00+02:00", "2026-03-30T00:00:00+02:00"]


def test_recording_intervals_not_dividing_a_day():
    recording = Recording(data_frequency="7h", data_frequency_timezone="UTC")

    grid = recording_grid("2026-01-01T00:00:00Z", "2026-01-02T07:00:00Z", recording)

    assert local(grid, "UTC") == [
        "2026-01-01T00:00:00+00:00",
        "2026-01-01T07:00:00+00:00",
        "2026-01-01T14:00:00+00:00",
        "2026-01-01T21:00:00+00:00",
        "2026-01-02T00:00:00+00:00",
        "2026-01-02T07:00:00+00:00",
    ]


def test_recording_intervals_with_offset_in_local_time():
    # the intervals of a day start at local midnight plus offset
    recording = Recording(
        data_frequency="6h", data_frequency_offset="30min", data_frequency_timezone="Asia/Kolkata"
    )

    starts = recording_interval_starts(
        utc("2026-01-01T18:30:00Z", "2026-01-01T19:00:00Z"), recording
    )

    assert local(starts, "Asia/Kolkata") == [
        "2026-01-01T18:30:00+05:30",
        "2026-01-02T00:30:00+05:30",
    ]


def test_recording_intervals_of_local_days_and_months():
    # the clocks are put back at 03:00 local time on 2026-10-25, so the day has 25 hours
    days = recording_grid(
        "2026-10-24T00:00:00Z",
        "2026-10-27T00:00:00Z",
        Recording(data_frequency="1D", data_frequency_timezone="Europe/Berlin"),
    )
    months = recording_grid(
        "2026-01-15T00:00:00Z",
        "2026-04-02T00:00:00Z",
        Recording(data_frequency="MS", data_frequency_timezone="Europe/Berlin"),
    )

    assert local(days) == [
        "2026-10-25T00:00:00+02:00",
        "2026-10-26T00:00:00+01:00",
        "2026-10-27T00:00:00+01:00",
    ]
    assert local(months) == [
        "2026-02-01T00:00:00+01:00",
        "2026-03-01T00:00:00+01:00",
        "2026-04-01T00:00:00+02:00",
    ]


def test_recording_interval_starts_of_series_and_naive_timestamps():
    timestamps = pd.Series(
        pd.to_datetime(["2026-01-01T00:07:00", "2026-01-01T00:29:00"]), index=["a", "b"]
    )

    starts = recording_interval_starts(timestamps, Recording(data_frequency="15min"))

    assert starts.index.to_list() == ["a", "b"]
    assert starts.to_list() == list(utc("2026-01-01T00:00:00Z", "2026-01-01T00:15:00Z"))


def test_recording_grid_from_start_to_end():
    recording = Recording(data_frequency="15min")

    assert recording_grid("2026-01-01T00:15:00Z", "2026-01-01T00:30:00Z", recording).equals(
        utc("2026-01-01T00:15:00Z", "2026-01-01T00:30:00Z")
    )
    assert len(recording_grid("2026-01-01T00:01:00Z", "2026-01-01T00:14:00Z", recording)) == 0
    assert len(recording_grid("2026-01-02T00:00:00Z", "2026-01-01T00:00:00Z", recording)) == 0


@pytest.mark.parametrize(
    "recording",
    [
        Recording(recording_mode="periodic"),
        Recording(data_frequency="36h", data_frequency_timezone="Europe/Berlin"),
    ],
)
def test_recording_without_usable_frequency(recording):
    with pytest.raises(ValueError, match="data_frequency|calendar"):
        recording_interval_starts(utc("2026-01-01T00:00:00Z"), recording)
