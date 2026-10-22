"""Default time zone of the metrics, falling back to the one of the dataset metadata"""

import pandas as pd
import pytest

from hdhelpers.helpers import modify_timezone
from hdhelpers.metadata import (
    get_default_timezones,
    get_series_default_timezone,
    get_singlets_default_timezone,
)


def frame(attrs):
    df = pd.DataFrame()
    df.attrs = attrs
    return df


def series(attrs, values=(1.0,), timestamps=("2026-03-29T12:00:00Z",)):
    ser = pd.Series(list(values), index=pd.to_datetime(list(timestamps)))
    ser.attrs = attrs
    return ser


multitsframe_attrs = {
    "dataset_metadata": {"metric_key": "external_id", "default_timezone": "Europe/Berlin"},
    "metrics": [
        {"external_id": "new_york", "default_timezone": "America/New_York"},
        {"external_id": "fixed_offset", "default_timezone": "+02:00"},
        {"external_id": "without"},
        {"external_id": "null", "default_timezone": None},
        {"external_id": "no_string", "default_timezone": 2},
        {"external_id": "empty", "default_timezone": ""},
    ],
}


def test_default_timezones_of_metrics_fall_back_to_dataset_metadata():
    timezones = get_default_timezones(frame(multitsframe_attrs))

    assert timezones == {
        "new_york": "America/New_York",
        "fixed_offset": "+02:00",
        "without": "Europe/Berlin",
        "null": "Europe/Berlin",
        "no_string": "Europe/Berlin",
        "empty": "Europe/Berlin",
    }
    # the default time zone of the dataset metadata applies to all metrics without their own
    assert timezones["metric without metadata"] == "Europe/Berlin"


def test_default_timezones_without_dataset_default_timezone():
    attrs = {"metrics": [{"id": "a", "default_timezone": "UTC"}, {"id": "b"}]}

    timezones = get_default_timezones(frame(attrs))

    assert timezones == {"a": "UTC", "b": None}
    assert timezones["metric without metadata"] is None


def test_default_timezone_does_not_fall_back_to_other_levels():
    """The conventions specify only the dataset metadata as fallback"""
    attrs = {
        "dataset_metadata": {"single_metric": "a"},
        "metrics": [
            {
                "id": "a",
                "inherited": {"default_timezone": "Asia/Tokyo"},
                "value_dimensions": [{"column": "value", "default_timezone": "Asia/Tokyo"}],
            }
        ],
        "value_dimensions_shared": [{"column": "value", "default_timezone": "Asia/Tokyo"}],
    }

    assert get_default_timezones(frame(attrs))["a"] is None
    assert get_series_default_timezone(series(attrs)) is None
    assert get_singlets_default_timezone(frame(attrs)) is None


@pytest.mark.parametrize(
    ("attrs", "expected"),
    [
        (
            {
                "dataset_metadata": {"single_metric": "a", "default_timezone": "Europe/Berlin"},
                "metrics": [{"id": "a", "default_timezone": "America/New_York"}],
            },
            "America/New_York",
        ),
        (
            {
                "dataset_metadata": {"single_metric": "a", "default_timezone": "Europe/Berlin"},
                "metrics": [{"id": "a", "default_timezone": None}],
            },
            "Europe/Berlin",
        ),
        # without single_metric the only metric is used
        ({"metrics": [{"id": "a", "default_timezone": "UTC"}]}, "UTC"),
        # without metric metadata the dataset metadata still applies
        ({"dataset_metadata": {"default_timezone": "Europe/Berlin"}}, "Europe/Berlin"),
        (
            {"dataset_metadata": {"default_timezone": "Europe/Berlin"}, "metrics": []},
            "Europe/Berlin",
        ),
        ({}, None),
        # older metadata structures do not provide default time zones of the metrics
        ({"by_metric": {"series": {"metric": {"default_timezone": "UTC"}}}}, None),
    ],
)
def test_default_timezone_of_single_metric(attrs, expected):
    assert get_series_default_timezone(series(attrs)) == expected
    assert get_singlets_default_timezone(frame(attrs)) == expected


def test_wrong_types_raise():
    with pytest.raises(TypeError):
        get_default_timezones(series({}))
    with pytest.raises(TypeError):
        get_series_default_timezone(frame({}))
    with pytest.raises(TypeError):
        get_singlets_default_timezone(series({}))


def test_aggregating_days_in_default_timezone():
    """As in the first steps: days start at midnight of the default time zone, which may
    differ from UTC days and changes its UTC offset with daylight saving time"""
    attrs = {
        "dataset_metadata": {"single_metric": "a"},
        "metrics": [{"id": "a", "default_timezone": "Europe/Berlin"}],
    }
    # 2026-03-29 is the day daylight saving time starts in Germany, it has 23 hours
    hourly = series(
        attrs,
        values=[1.0] * 26,
        timestamps=pd.date_range("2026-03-28T23:00:00Z", periods=26, freq="1h"),
    )

    timezone = get_series_default_timezone(hourly) or "UTC"
    daily_sums = modify_timezone(hourly, to_timezone=timezone).resample("1D").sum()

    assert daily_sums.to_dict() == {
        pd.Timestamp("2026-03-29", tz="Europe/Berlin"): 23.0,
        pd.Timestamp("2026-03-30", tz="Europe/Berlin"): 3.0,
    }
