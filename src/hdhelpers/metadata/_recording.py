"""How the values of the metrics are recorded and how they should be aggregated by default

The frequency of the recorded values of a metric falls back as a whole: If the metric has a
"data_frequency", it applies together with the metric's "data_frequency_offset" and
"data_frequency_timezone". Otherwise "ref_data_frequency" of the dataset metadata applies
together with "ref_data_frequency_offset" and "ref_data_frequency_timezone". A missing offset
is 0.

The recording intervals start at the multiples of the frequency plus the offset. Without time
zone these are the multiples since 1970-01-01T00:00:00Z. With time zone and a frequency shorter
than a day, the intervals restart at each local midnight (plus offset) of the time zone, counted
in elapsed time, and the last interval of a day ends at the next local midnight. With time zone
and a frequency of a day or longer, the intervals follow the calendar of the time zone, e.g.
local days of 23, 24 or 25 hours.
"""

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, TypeIs, cast

import pandas as pd

import hdhelpers.metadata._current_convention as _current_convention
from hdhelpers.metadata._helpers import _select_single_metric, _string_or_none

_FREQUENCY_FIELDS = ("data_frequency", "data_frequency_offset", "data_frequency_timezone")
_DATASET_FREQUENCY_FIELDS = (
    "ref_data_frequency",
    "ref_data_frequency_offset",
    "ref_data_frequency_timezone",
)

# default aggregation method of metrics without one by the data type of their values
_DEFAULT_AGGREGATION_METHOD_BY_VALUE_DATA_TYPE = {"boolean": "LAST", "string": "LAST"}
_DEFAULT_AGGREGATION_METHOD = "MEAN"
_AGGREGATION_METHOD_ALIASES = {"AVG": "MEAN"}

_DAY = pd.Timedelta(days=1)


@dataclass(frozen=True)
class Recording:
    """How the values of a metric are recorded

    The fields are taken from the metadata as given. data_frequency_offset and
    data_frequency_timezone belong to data_frequency: They are None if no data_frequency
    applies. A data_frequency_offset of None means 0.
    """

    recording_mode: str | None = None
    data_frequency: str | None = None
    data_frequency_offset: str | None = None
    data_frequency_timezone: str | None = None
    recording_aggregation_method: str | None = None


_Frequency = tuple[str | None, str | None, str | None]
_NO_FREQUENCY: _Frequency = (None, None, None)


def _frequency(obj: Any, fields: tuple[str, str, str]) -> _Frequency:
    """Frequency, offset and time zone of obj, all None if it has no frequency

    Values which are no (non-empty) strings count as missing.
    """
    if not isinstance(obj, dict):
        return _NO_FREQUENCY
    frequency, offset, timezone = (_string_or_none(obj.get(field)) for field in fields)
    if frequency is None:
        return _NO_FREQUENCY
    return frequency, offset, timezone


def _dataset_frequency(attrs: Any) -> _Frequency:
    dataset_metadata = attrs.get("dataset_metadata") if isinstance(attrs, dict) else None
    return _frequency(dataset_metadata, _DATASET_FREQUENCY_FIELDS)


def _recording(metric: dict, dataset_frequency: _Frequency) -> Recording:
    own_frequency = _frequency(metric, _FREQUENCY_FIELDS)
    frequency, offset, timezone = (
        own_frequency if own_frequency[0] is not None else dataset_frequency
    )
    return Recording(
        recording_mode=_string_or_none(metric.get("recording_mode")),
        data_frequency=frequency,
        data_frequency_offset=offset,
        data_frequency_timezone=timezone,
        recording_aggregation_method=_string_or_none(metric.get("recording_aggregation_method")),
    )


def recording_by_metric(data: pd.DataFrame | pd.Series) -> defaultdict[str, Recording]:
    """The recording of each metric, falling back to the frequency of the dataset metadata

    The default of the returned defaultdict is the recording of a metric without metadata, i.e.
    with the frequency of the dataset metadata.
    """
    dataset_frequency = _dataset_frequency(data.attrs)
    gathered = _current_convention.gather(data.attrs)
    metrics = (
        {}
        if gathered is None
        else {
            metric: gathered_metric.metric for metric, gathered_metric in gathered.metrics.items()
        }
    )
    return defaultdict(
        lambda: Recording(None, *dataset_frequency, None),
        {metric: _recording(obj, dataset_frequency) for metric, obj in metrics.items()},
    )


def single_metric_recording(data: pd.DataFrame | pd.Series) -> Recording:
    """The recording of the single metric of a Series or SingleTSFrame

    Falls back to the frequency of the dataset metadata, also if the single metric is not found.
    """
    return cast(
        Recording,
        _select_single_metric(
            recording_by_metric(data),
            data.attrs,
            empty=Recording(None, *_dataset_frequency(data.attrs), None),
        ),
    )


def _default_aggregation_method(method: Any, value_data_type: Any) -> str:
    own_method = _string_or_none(method)
    if own_method is not None:
        return _AGGREGATION_METHOD_ALIASES.get(own_method, own_method)
    return _DEFAULT_AGGREGATION_METHOD_BY_VALUE_DATA_TYPE.get(
        value_data_type, _DEFAULT_AGGREGATION_METHOD
    )


def default_aggregation_method_by_metric(data: pd.DataFrame | pd.Series) -> defaultdict[str, str]:
    """The default aggregation method of each metric

    The method of the metric, with "AVG" normalized to its alias "MEAN". If the metric does not
    provide one, "LAST" for values of the data type "boolean" or "string" (of the value
    dimension "value", see value_dimension_info) and "MEAN" otherwise, which is also the default
    of the returned defaultdict.
    """
    gathered = _current_convention.gather(data.attrs)
    if gathered is None:
        return defaultdict(lambda: _DEFAULT_AGGREGATION_METHOD)
    methods = _current_convention.own_metric_info(gathered, "default_aggregation_method")
    value_data_types = _current_convention.value_dimension_info(
        gathered, ["value_data_type"], include_inherited=False
    )
    return defaultdict(
        lambda: _DEFAULT_AGGREGATION_METHOD,
        {
            metric: _default_aggregation_method(method, value_data_types[metric]["value"])
            for metric, method in methods.items()
        },
    )


def single_metric_default_aggregation_method(data: pd.DataFrame | pd.Series) -> str:
    """The default aggregation method of the single metric of a Series or SingleTSFrame"""
    return cast(
        str,
        _select_single_metric(
            default_aggregation_method_by_metric(data),
            data.attrs,
            empty=_DEFAULT_AGGREGATION_METHOD,
        ),
    )


def _grid_parameters(
    recording: Recording,
) -> tuple[pd.offsets.BaseOffset, pd.Timedelta, str | None]:
    """Frequency as Pandas offset, offset as Timedelta and time zone of a recording"""
    if recording.data_frequency is None:
        raise ValueError("The recording has no data_frequency, which defines its intervals.")
    try:
        frequency = pd.tseries.frequencies.to_offset(recording.data_frequency)
    except ValueError:
        # e.g. "P1D" or "1 days"
        frequency = pd.tseries.frequencies.to_offset(
            pd.to_timedelta(recording.data_frequency)  # type: ignore[call-overload]
        )
    offset = pd.to_timedelta(recording.data_frequency_offset or "0s")
    return frequency, offset, recording.data_frequency_timezone


def _is_shorter_than_a_day(frequency: pd.offsets.BaseOffset) -> TypeIs[pd.offsets.Tick]:
    return isinstance(frequency, pd.offsets.Tick) and pd.Timedelta(frequency) < _DAY


def _utc_series(timestamps: pd.DatetimeIndex | pd.Series) -> pd.Series:
    """Timestamps as Series in UTC, naive timestamps are considered to be UTC"""
    series = pd.Series(timestamps) if isinstance(timestamps, pd.DatetimeIndex) else timestamps
    if series.dt.tz is None:
        return series.dt.tz_localize("UTC")
    return series.dt.tz_convert("UTC")


def _localize_midnights(naive_midnights: pd.Series, timezone: str) -> pd.Series:
    """Localize local midnights, shifting nonexistent ones forward and preferring DST"""
    return naive_midnights.dt.tz_localize(
        timezone, ambiguous=[True] * len(naive_midnights), nonexistent="shift_forward"
    )


def _calendar_interval_starts(
    utc: pd.Series, frequency: pd.offsets.BaseOffset, offset: pd.Timedelta, timezone: str
) -> pd.Series:
    """Interval starts of a frequency of a day or longer in the calendar of the time zone"""
    local_days = (utc - offset).dt.tz_convert(timezone).dt.tz_localize(None).dt.normalize()
    if isinstance(frequency, pd.offsets.Day | pd.offsets.Tick):
        step = (
            frequency.n * _DAY if isinstance(frequency, pd.offsets.Day) else pd.Timedelta(frequency)
        )
        if step % _DAY != pd.Timedelta(0):
            raise ValueError(
                f'A frequency of "{frequency.freqstr}" cannot follow the calendar of a time zone,'
                " only multiples of a day can."
            )
        # multiples of whole days since 1970-01-01 in local time
        epoch = pd.Timestamp("1970-01-01")
        starts = epoch + ((local_days - epoch) // step) * step
    else:
        # e.g. the first day of the month for "MS"
        unique_starts = {day: frequency.rollback(day) for day in local_days.dropna().unique()}
        starts = local_days.map(unique_starts).astype(local_days.dtype)
    return _localize_midnights(starts, timezone) + offset


def recording_interval_starts[T: (pd.DatetimeIndex, pd.Series)](
    timestamps: T, recording: Recording
) -> T:
    """The start of the recording interval of each timestamp, in UTC"""
    frequency, offset, timezone = _grid_parameters(recording)
    utc = _utc_series(timestamps)

    if timezone is None and isinstance(frequency, pd.offsets.Tick):
        epoch = pd.Timestamp(0, tz="UTC")
        duration = pd.Timedelta(frequency)
        starts = epoch + offset + ((utc - epoch - offset) // duration) * duration
    elif timezone is not None and _is_shorter_than_a_day(frequency):
        duration = pd.Timedelta(frequency)
        # the intervals of a day start at its local midnight plus offset
        local_midnights = (utc - offset).dt.tz_convert(timezone).dt.normalize()
        day_starts = local_midnights.dt.tz_convert("UTC") + offset
        starts = day_starts + ((utc - day_starts) // duration) * duration
    else:
        starts = _calendar_interval_starts(utc, frequency, offset, timezone or "UTC").dt.tz_convert(
            "UTC"
        )

    if isinstance(timestamps, pd.DatetimeIndex):
        return pd.DatetimeIndex(starts.to_numpy(), name=timestamps.name)
    return starts.set_axis(timestamps.index)


def recording_grid(
    start: pd.Timestamp, end: pd.Timestamp, recording: Recording
) -> pd.DatetimeIndex:
    """The recording interval starts from start to end, both inclusive, in UTC"""
    frequency, offset, timezone = _grid_parameters(recording)
    start = _utc_series(pd.DatetimeIndex([start])).iloc[0]
    end = _utc_series(pd.DatetimeIndex([end])).iloc[0]
    if start > end:
        return pd.DatetimeIndex([], tz="UTC")
    first = recording_interval_starts(pd.DatetimeIndex([start]), recording)[0]

    if timezone is None and isinstance(frequency, pd.offsets.Tick):
        grid = pd.date_range(first, end, freq=pd.Timedelta(frequency))
    elif timezone is not None and _is_shorter_than_a_day(frequency):
        duration = pd.Timedelta(frequency)
        local_midnights = pd.date_range(
            (first - offset).tz_convert(timezone).normalize(),
            (end - offset).tz_convert(timezone).normalize() + _DAY,
            freq="D",
        )
        day_starts = local_midnights.tz_convert("UTC") + offset
        grid = pd.DatetimeIndex(
            [
                day_start + index * duration
                for day_start, next_day_start in zip(day_starts[:-1], day_starts[1:], strict=True)
                for index in range(math.ceil((next_day_start - day_start) / duration))
            ],
            tz="UTC",
        )
    else:
        # step through the calendar of the time zone via the interval starts of the days
        days = pd.date_range(
            (first - offset).tz_convert(timezone or "UTC").normalize().tz_localize(None),
            (end - offset).tz_convert(timezone or "UTC").normalize().tz_localize(None),
            freq="D",
        )
        candidates = (
            _localize_midnights(pd.Series(days), timezone or "UTC").dt.tz_convert("UTC") + offset
        )
        grid = pd.DatetimeIndex(
            recording_interval_starts(pd.DatetimeIndex(candidates), recording).unique()
        )

    return grid[(grid >= start) & (grid <= end)]
