"""Analyze time intervals and sampling modes of a measurement series.

Explicit arguments and recording metadata take precedence over heuristics derived from the
Basic Quality Check (SERIES) component. A known recording mode defines expected sampling, not
the actual alignment of timestamps to a grid. Change-only detection is only inferred when the
recording mode is unknown. An on_change heartbeat is kept separate from the sampling interval.

This module does not filter outliers, choose a target grid, detect gaps or modify input metadata.
Analyze the original series before filtering, so removed values do not change its sampling profile.
"""

import datetime
from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from hdhelpers.helpers import parse_fixed_frequency
from hdhelpers.metadata import Recording, get_queried_interval, get_series_recording
from hdhelpers.metadata.helpers import check_series

FrequencySource = Literal["provided", "metadata", "auto"]

MIN_TIMESTAMPS_FOR_FREQUENCY = 3
REGULAR_SAMPLING_MIN_SHARE = 0.8
REGULAR_STEP_MIN_FACTOR = 0.5
REGULAR_STEP_MAX_FACTOR = 1.5
CHANGE_ONLY_MAX_SMALL_CHANGE_SHARE = 0.05
CHANGE_ONLY_SMALL_CHANGE_FRACTION = 0.25
MIN_CHANGES_FOR_CHANGE_ONLY = 20


@dataclass(frozen=True)
class SamplingAnalysis:
    """Sampling information determined before quality filtering.

    frequency is an explicitly supplied interval, a fixed recording interval, or an estimate
    from all distinct timestamps, including invalid measurement values. An on_change metadata
    frequency is a heartbeat and is never substituted for the sampling interval. In that case,
    frequency is estimated unless explicitly supplied. Its source is "auto" even if too few
    timestamps prevent an estimate.
    regular_sampling follows a known recording mode; otherwise it is inferred from the interval
    source and timestamps. For compatibility, an unknown interval alone does not imply irregularity.
    change_only follows an explicit argument, then a known recording mode, then a value heuristic.
    An inferred False is not proof of a non-change-only signal, especially for short series.
    typical_pause is the time-weighted median pause, including query boundaries when available.
    heartbeat is the maximum recording pause from on_change metadata, or None if unavailable.
    All durations are pandas Timedelta objects, not JSON strings.
    """

    frequency: pd.Timedelta | None
    frequency_source: FrequencySource
    regular_sampling: bool
    change_only: bool
    typical_pause: pd.Timedelta | None
    heartbeat: pd.Timedelta | None = None


def _utc_index(index: pd.Index) -> pd.DatetimeIndex:
    """Normalize timestamps without changing their order or dropping duplicates."""
    if len(index) == 0:
        return pd.DatetimeIndex([], tz="UTC").as_unit("ns")
    if not isinstance(index, pd.DatetimeIndex):
        if pd.api.types.is_numeric_dtype(index.dtype):
            raise ValueError("The series index must contain timestamps, not numbers.")
        index = pd.DatetimeIndex(pd.to_datetime(index, utc=True))
    if index.hasnans:
        raise ValueError("The series index must not contain NaT timestamps.")
    return (index.tz_localize("UTC") if index.tz is None else index.tz_convert("UTC")).as_unit("ns")


def _sorted_timestamps(timestamps: pd.DatetimeIndex) -> pd.DatetimeIndex:
    index = _utc_index(timestamps)
    if index.has_duplicates:
        index = index.unique()
    return index if index.is_monotonic_increasing else index.sort_values()


def _recording_frequency(recording: Recording) -> pd.Timedelta | None:
    if recording.data_frequency is None:
        return None
    try:
        return parse_fixed_frequency(recording.data_frequency)
    except ValueError:
        return None


def parse_frequency_from_metadata(series: pd.Series) -> pd.Timedelta | None:
    """Parse the fixed frequency returned by the recording metadata getter.

    get_series_recording resolves metric frequency before dataset frequency and supports raw
    convention metadata and attached models. Missing or invalid metadata and calendar-based
    frequencies return None. For on_change, the returned duration is the heartbeat, not the
    sampling interval; analyze_sampling exposes it separately as heartbeat.
    """
    return _recording_frequency(get_series_recording(series))


def determine_data_frequency(timestamps: pd.DatetimeIndex) -> pd.Timedelta | None:
    """Estimate the interval from the lower median of consecutive timestamp differences.

    Timestamps are sorted and deduplicated. At least three distinct timestamps are needed.
    For an even number of differences, the lower middle value is used, since gaps only make
    differences longer.
    """
    timestamps = _sorted_timestamps(timestamps)
    if len(timestamps) < MIN_TIMESTAMPS_FOR_FREQUENCY:
        return None
    differences = pd.Series(timestamps[1:] - timestamps[:-1])
    return differences.quantile(0.5, interpolation="lower")


def _resolve_data_frequency(
    all_timestamps: pd.DatetimeIndex,
    data_frequency: str | pd.Timedelta | None,
    recording: Recording,
) -> tuple[pd.Timedelta | None, FrequencySource]:
    if data_frequency is not None:
        return parse_fixed_frequency(data_frequency), "provided"
    if (
        recording.recording_mode != "on_change"
        and (frequency := _recording_frequency(recording)) is not None
    ):
        return frequency, "metadata"
    return determine_data_frequency(all_timestamps), "auto"


def resolve_data_frequency(
    series: pd.Series,
    all_timestamps: pd.DatetimeIndex,
    data_frequency: str | pd.Timedelta | None = None,
) -> tuple[pd.Timedelta | None, FrequencySource]:
    """Resolve an explicit interval, recording interval or timestamp estimate.

    An on_change recording frequency describes a heartbeat, so timestamps are used instead
    unless data_frequency is explicitly supplied.
    """
    return _resolve_data_frequency(all_timestamps, data_frequency, get_series_recording(series))


def is_regular_sampling(timestamps: pd.DatetimeIndex, frequency: pd.Timedelta | None) -> bool:
    """Check whether at least 80% of intervals lie between 0.5 and 1.5 times frequency.

    This permits timestamp jitter and some missing observations; it does not check alignment
    to a fixed grid. Unknown frequency or no intervals is treated as regular, as in the component.
    """
    timestamps = _sorted_timestamps(timestamps)
    if frequency is None or len(timestamps) < 2:
        return True
    frequency = parse_fixed_frequency(frequency)
    differences = pd.Series(timestamps[1:] - timestamps[:-1])
    return bool(
        differences.between(
            REGULAR_STEP_MIN_FACTOR * frequency, REGULAR_STEP_MAX_FACTOR * frequency
        ).mean()
        >= REGULAR_SAMPLING_MIN_SHARE
    )


def is_change_only(series: pd.Series) -> bool:
    """Heuristically detect send-on-change behavior in time-sorted finite numeric values.

    At least 20 consecutive changes are needed. Fewer than 5% must be smaller than one quarter
    of the median absolute change, and the median must be positive. Constant signals and short
    series return False because they do not provide enough evidence.
    """
    changes = np.abs(np.diff(series.to_numpy(dtype=float)))
    if len(changes) < MIN_CHANGES_FOR_CHANGE_ONLY:
        return False
    median_change = float(np.median(changes))
    small_change_share = np.mean(changes < CHANGE_ONLY_SMALL_CHANGE_FRACTION * median_change)
    return median_change > 0 and bool(small_change_share < CHANGE_ONLY_MAX_SMALL_CHANGE_SHARE)


def typical_pause(
    timestamps: pd.DatetimeIndex,
    interval_start: datetime.datetime | None = None,
    interval_end: datetime.datetime | None = None,
) -> pd.Timedelta | None:
    """Time-weighted median pause between distinct timestamps, optionally including boundaries.

    Half of the time lies in pauses no longer than the result. Query boundaries are interpreted
    as UTC if timezone-naive. Empty timestamps or zero total duration return None.
    """
    times_ns = _sorted_timestamps(timestamps).asi8
    pauses = [np.diff(times_ns)]
    for boundary, is_start in ((interval_start, True), (interval_end, False)):
        if len(times_ns) > 0 and boundary is not None:
            boundary_ns = _utc_index(pd.DatetimeIndex([boundary])).asi8[0]
            duration = times_ns[0] - boundary_ns if is_start else boundary_ns - times_ns[-1]
            pauses.append(np.array([max(duration, 0)]))
    sorted_pauses = np.sort(np.concatenate(pauses))
    if len(sorted_pauses) == 0 or sorted_pauses.sum() == 0:
        return None
    return pd.Timedelta(
        int(sorted_pauses[np.searchsorted(np.cumsum(sorted_pauses), sorted_pauses.sum() / 2)]),
        "ns",
    )


def analyze_sampling(
    series: pd.Series,
    *,
    data_frequency: str | pd.Timedelta | None = None,
    change_only: bool | None = None,
) -> SamplingAnalysis:
    """Analyze sampling without modifying the series or its attrs.

    Timezone-naive timestamps are UTC. Values are sorted, finite numeric values are retained
    for change-only detection, and duplicate timestamps are averaged for that detection only.
    Frequency and pause estimates use all distinct input timestamps, including invalid values.
    An explicit change_only overrides the change-only decision. Otherwise a known recording
    mode takes precedence over heuristics: periodic is regular, irregular and on_change are not.
    Only unknown modes use automatic change-only detection on irregular sampling.
    An on_change metadata frequency is returned as heartbeat, while the sampling interval is
    estimated from timestamps unless data_frequency is explicitly supplied.

    Raises:
        TypeError: series is not a pandas Series, or a supplied parameter has an invalid type.
        ValueError: Timestamps, non-null values or an explicit data_frequency are invalid.
    """
    check_series(series)
    if change_only is not None and not isinstance(change_only, bool):
        raise TypeError("change_only must be a bool or None.")
    index = _utc_index(series.index)
    values = pd.to_numeric(series, errors="coerce").to_numpy(dtype=float, na_value=np.nan)
    if np.all(np.isnan(values)) and series.notna().any():
        raise ValueError("The values of series must be numeric.")
    prepared = pd.Series(values, index=index).sort_index(kind="stable")
    prepared = prepared[np.isfinite(prepared.to_numpy())]
    if prepared.index.has_duplicates:
        prepared = prepared.groupby(level=0).mean()
    all_timestamps = _sorted_timestamps(index)
    recording = get_series_recording(series)
    frequency, source = _resolve_data_frequency(all_timestamps, data_frequency, recording)
    if recording.recording_mode is None:
        regular = source != "auto" or is_regular_sampling(all_timestamps, frequency)
    else:
        regular = recording.recording_mode == "periodic"
    if change_only is None:
        change_only = (
            not regular and is_change_only(prepared)
            if recording.recording_mode is None
            else recording.recording_mode == "on_change"
        )
    start, end = get_queried_interval(series)
    return SamplingAnalysis(
        frequency=frequency,
        frequency_source=source,
        regular_sampling=regular and not change_only,
        change_only=change_only,
        typical_pause=typical_pause(all_timestamps, start, end),
        heartbeat=(
            _recording_frequency(recording) if recording.recording_mode == "on_change" else None
        ),
    )
