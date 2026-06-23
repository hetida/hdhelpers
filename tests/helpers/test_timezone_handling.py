import datetime
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from hdhelpers.helpers import modify_timezone
from hdhelpers.plot_target_settings import PlotTargetSettings


# tests
@pytest.mark.parametrize(
    ("timestamp", "timezone", "result"),
    [
        pytest.param("2025-01-01T01:00:00", None, datetime.timezone.utc, id="naive none"),
        pytest.param(
            "2025-01-01T01:00:00+05:00",
            None,
            datetime.timezone(datetime.timedelta(seconds=18000)),
            id="aware none",
        ),
    ],
)
def test_modify_timezone_timestamp_naive(timestamp, timezone, result):
    modified_timezone = modify_timezone(pd.to_datetime(timestamp), to_timezone=timezone)
    assert modified_timezone.tz == result


@pytest.mark.parametrize(
    ("timestamp", "timezone", "result"),
    [
        pytest.param(
            "2025-01-01T01:00:00",
            "Europe/Berlin",
            datetime.timedelta(seconds=3600),
            id="naive given",
        ),
        pytest.param(
            "2025-01-01T01:00:00+05:00",
            "Europe/Berlin",
            datetime.timedelta(seconds=3600),
            id="aware given",
        ),
    ],
)
def test_modify_timezone_timestamp_offset(timestamp, timezone, result):
    modified_timezone = modify_timezone(pd.to_datetime(timestamp), to_timezone=timezone)
    assert modified_timezone.utcoffset() == result


def test_modify_timezone_good_dataframe(dataframe):
    local_summertime = modify_timezone(
        dataframe, to_timezone="Europe/Berlin", column_names=["timestamp"]
    )

    # German summer time starts in last Sunday in March at 2 am. --> UTC 1am
    timestamp_id = local_summertime.columns.get_loc("timestamp")
    assert local_summertime.iloc[1, timestamp_id].utcoffset() == datetime.timedelta(seconds=7200)
    assert local_summertime.iloc[2, timestamp_id].utcoffset() == datetime.timedelta(seconds=7200)
    assert "foo" in local_summertime.attrs


def test_modify_timezone_good_series(series_summer, series_winter):
    local_summertime = modify_timezone(series_summer, to_timezone="Europe/Berlin")
    local_wintertime = modify_timezone(series_winter, to_timezone="Europe/Berlin")
    cet = modify_timezone(series_winter, to_timezone="CET")
    utc_wintertime = modify_timezone(local_wintertime, to_timezone="UTC")

    # German summer time starts in last Sunday in March at 2 am. --> UTC 1am
    assert local_summertime.index[1].utcoffset() == datetime.timedelta(seconds=3600)
    assert local_summertime.index[2].utcoffset() == datetime.timedelta(seconds=7200)
    assert "foo" in local_summertime.attrs

    # German winter time starts in last Sunday in October at 3 am. --> UTC: 1am
    assert local_wintertime.index[0].utcoffset() == datetime.timedelta(seconds=7200)
    assert local_wintertime.index[1].utcoffset() == datetime.timedelta(seconds=3600)
    assert "foo" in local_wintertime.attrs

    # cet is equal to German winter time
    assert local_wintertime.index[1] == cet.index[1]

    # reversing works
    pd.testing.assert_series_equal(series_winter, utc_wintertime)

    # timedelta not influneced by new timezone
    np.testing.assert_array_equal(
        pd.to_timedelta(local_summertime.index[1:] - local_summertime.index[:-1])
        .total_seconds()
        .values,
        [3600.0, 3600.0, 3600.0],
    )


def test_modify_timezone_wrong_tzname(series_summer):
    with pytest.raises(ValueError, match="Timezone not known*"):
        _ = modify_timezone(series_summer, to_timezone="Europe/Berlin2")

def test_empty_series():
    data = pd.Series()
    modified_data = modify_timezone(data, to_timezone="Europe/Berlin")
    assert modified_data.empty

def test_empty_dataframe():
    data = pd.DataFrame()
    modified_data = modify_timezone(data, to_timezone="Europe/Berlin", column_names=["timestamp"])
    assert modified_data.empty

def test_named_series(series_summer):
    data = pd.Series(series_summer.index)
    data.name = "timestamp"
    data.attrs = series_summer.attrs
    modified_data = modify_timezone(data, to_timezone="Europe/Berlin", column_names=["timestamp"])
    assert modified_data[1].utcoffset() == datetime.timedelta(seconds=3600)
    assert "foo" in modified_data.attrs


def test_named_series_using_index(series_summer):
    data = series_summer
    data.name = "timestamp"
    modified_data = modify_timezone(data, to_timezone="Europe/Berlin")
    assert modified_data.index[0].utcoffset() == datetime.timedelta(seconds=3600)
    assert "foo" in modified_data.attrs


def test_column_not_known(series_summer, dataframe):
    data = pd.Series(series_summer.index)
    data.name = "timestamp"

    with pytest.raises(KeyError, match="At least one column name*"):
        _ = modify_timezone(data, to_timezone="Europe/Berlin", column_names=["timestamp2"])

    with pytest.raises(KeyError, match="At least one column name*"):
        _ = modify_timezone(dataframe, to_timezone="Europe/Berlin", column_names=["timestamp2"])


def test_modify_timezone_no_tz_known(series_summer):
    series_summer.index = series_summer.index.tz_localize(None)
    with pytest.raises(TypeError, match="Entries to convert do not contain valid timestamps*"):
        _ = modify_timezone(series_summer, to_timezone="Europe/Berlin")


def test_modify_timezone_multicolumn_dataframe(multicolumn_frame):
    local_summertime = modify_timezone(
        multicolumn_frame.copy(),
        to_timezone="Europe/Berlin",
        column_names=["timestamp", "more_timestamps"],
        convert_index=True,
    )

    timestamp_id = local_summertime.columns.get_loc("timestamp")
    timestamp_id_2 = local_summertime.columns.get_loc("more_timestamps")
    assert local_summertime.iloc[1, timestamp_id].utcoffset() == datetime.timedelta(seconds=7200)
    assert local_summertime.iloc[1, timestamp_id_2].utcoffset() == datetime.timedelta(seconds=7200)
    assert local_summertime.index[0].utcoffset() == datetime.timedelta(seconds=7200)
    assert "foo" in local_summertime.attrs


def test_modify_timezone_multicolumn_dataframe_without_index(multicolumn_frame):
    local_summertime = modify_timezone(
        multicolumn_frame.copy(),
        to_timezone="Europe/Berlin",
        column_names=["timestamp", "more_timestamps"],
        convert_index=False,
    )

    # German summer time starts in last Sunday in March at 2 am. --> UTC 1am
    timestamp_id = local_summertime.columns.get_loc("timestamp")
    timestamp_id_2 = local_summertime.columns.get_loc("more_timestamps")
    assert local_summertime.iloc[1, timestamp_id].utcoffset() == datetime.timedelta(seconds=7200)
    assert local_summertime.iloc[1, timestamp_id_2].utcoffset() == datetime.timedelta(seconds=7200)
    assert (
        local_summertime.index[1].utcoffset() == multicolumn_frame.index[0].utcoffset()
    )  # index of dataframe is not modified
    assert "foo" in local_summertime.attrs


def test_plot_target_timezone(series_summer):
    plot_target_settings_mock = MagicMock(
        return_value=PlotTargetSettings(plot_target_timezone="Europe/Berlin")
    )
    with patch(
        "hdhelpers.plot_target_settings.get_plot_target_settings", plot_target_settings_mock
    ):
        modified_data = modify_timezone(series_summer)
        assert modified_data.index[1].utcoffset() == datetime.timedelta(seconds=3600)


def test_modify_timestamp():
    modified_timestamp = modify_timezone(
        pd.to_datetime("2023-03-25 23:00", utc=True), to_timezone="Europe/Berlin"
    )
    assert modified_timestamp.utcoffset() == datetime.timedelta(seconds=3600)

def test_modify_timestamp_datetime():
    example_date = pd.to_datetime("2023-03-25 23:00", utc=True)
    modified_timestamp = modify_timezone(
        example_date.to_pydatetime(), to_timezone="Europe/Berlin"
    )
    assert modified_timestamp.utcoffset() == datetime.timedelta(seconds=3600)
