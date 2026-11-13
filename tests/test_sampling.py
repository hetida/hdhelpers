"""Sampling heuristics and their use on unfiltered measurement series."""

import copy

import numpy as np
import pandas as pd
import pytest

from hdhelpers.metadata import attach_metadata
from hdhelpers.metadata.conventions import SERIES_METADATA_EXAMPLE
from hdhelpers.sampling import (
    analyze_sampling,
    determine_data_frequency,
    is_change_only,
    is_regular_sampling,
    parse_frequency_from_metadata,
    resolve_data_frequency,
    typical_pause,
)


def regular_series(values) -> pd.Series:
    return pd.Series(values, index=pd.date_range("2026-01-01", periods=len(values), freq="1min"))


def burst_series(values=None) -> pd.Series:
    steps = np.tile([1, 1, 1, 1, 30, 300], 10)
    if values is None:
        values = np.arange(len(steps), dtype=float)
    return pd.Series(
        values,
        index=pd.Timestamp("2026-01-01T00:00:00Z") + pd.to_timedelta(np.cumsum(steps), unit="s"),
    )


def recording_series(
    metric_frequency=None, dataset_frequency=None, recording_mode=None
) -> pd.Series:
    series = regular_series([1.0, 2.0, 3.0])
    series.attrs = copy.deepcopy(SERIES_METADATA_EXAMPLE)
    series.attrs["metrics"][0]["recording_mode"] = recording_mode
    series.attrs["metrics"][0]["recording_aggregation_method"] = None
    series.attrs["metrics"][0]["data_frequency"] = metric_frequency
    series.attrs["dataset_metadata"]["ref_data_frequency"] = dataset_frequency
    return series


@pytest.mark.parametrize("count", [0, 1, 2])
def test_frequency_needs_three_distinct_timestamps(count):
    assert determine_data_frequency(regular_series(np.ones(count)).index) is None


def test_frequency_uses_lower_median_and_distinct_sorted_timestamps():
    timestamps = pd.DatetimeIndex(
        ["2026-01-01 00:03", "2026-01-01 00:00", "2026-01-01 00:01", "2026-01-01 00:01"]
    )
    assert determine_data_frequency(timestamps) == pd.Timedelta("1min")


@pytest.mark.parametrize(
    ("metric_frequency", "dataset_frequency", "expected"),
    [
        (None, None, None),
        ("5min", None, "5min"),
        (None, "2min", "2min"),
        ("5min", "2min", "5min"),
        ("D", None, "1D"),
        ("0s", None, None),
        ("5", None, None),
        ("ME", None, None),
        ("bad", "5min", None),
        (None, "bad", None),
        (60, None, None),
    ],
)
def test_metadata_frequency_uses_recording_conventions(
    metric_frequency, dataset_frequency, expected
):
    series = recording_series(metric_frequency, dataset_frequency)
    assert parse_frequency_from_metadata(series) == (pd.Timedelta(expected) if expected else None)


@pytest.mark.parametrize(
    "attrs",
    [
        {},
        {"ref_data_frequency": "5min"},
        {"dataset_metadata": {"ref_data_frequency": "5min"}},
        {"dataset_metadata": "invalid"},
    ],
)
def test_missing_or_invalid_metadata_falls_back_to_timestamp_estimate(attrs):
    series = regular_series([1.0, 2.0, 3.0])
    series.attrs = attrs
    assert parse_frequency_from_metadata(series) is None
    analysis = analyze_sampling(series)
    assert analysis.frequency == pd.Timedelta("1min")
    assert analysis.frequency_source == "auto"


@pytest.mark.parametrize(
    ("metric_frequency", "dataset_frequency", "expected"),
    [("2min", "5min", "2min"), (None, "5min", "5min")],
)
def test_frequency_from_attached_metadata_models(metric_frequency, dataset_frequency, expected):
    series = recording_series(metric_frequency, dataset_frequency)
    assert attach_metadata(series) is not None
    assert "metrics" not in series.attrs
    assert "dataset_metadata" not in series.attrs
    assert parse_frequency_from_metadata(series) == pd.Timedelta(expected)
    analysis = analyze_sampling(series)
    assert analysis.frequency == pd.Timedelta(expected)
    assert analysis.frequency_source == "metadata"


@pytest.mark.parametrize("frequency", ["30s", pd.Timedelta("30s")])
def test_explicit_frequency_takes_precedence_over_metadata(frequency):
    series = recording_series(metric_frequency="5min")
    assert resolve_data_frequency(series, series.index, frequency) == (
        pd.Timedelta("30s"),
        "provided",
    )


@pytest.mark.parametrize("frequency", ["0s", "-1min", "5", "ME", "NaT", pd.Timedelta(0)])
def test_invalid_explicit_frequency_is_not_silently_replaced(frequency):
    series = recording_series(metric_frequency="5min")
    with pytest.raises(ValueError, match="positive fixed duration"):
        analyze_sampling(series, data_frequency=frequency)


@pytest.mark.parametrize(
    ("steps", "expected"),
    [([30, 90, 60, 60, 200], True), ([30, 90, 60, 200, 200], False)],
)
def test_regular_sampling_includes_tolerance_boundaries_and_requires_eighty_percent(
    steps, expected
):
    timestamps = pd.DatetimeIndex(
        pd.Timestamp("2026-01-01") + pd.to_timedelta(np.r_[0, np.cumsum(steps)], unit="s")
    )
    assert is_regular_sampling(timestamps, pd.Timedelta("1min")) is expected


def test_regularity_does_not_require_alignment_to_full_minutes():
    timestamps = pd.date_range("2026-01-01T00:00:17Z", periods=30, freq="1min")
    assert is_regular_sampling(timestamps, pd.Timedelta("1min"))


@pytest.mark.parametrize("values", [np.ones(30), np.arange(20), np.tile([0.0, 1.0, 1.1], 10)])
def test_change_only_needs_enough_changes_and_few_small_changes(values):
    assert not is_change_only(regular_series(values))


def test_change_only_requires_at_least_twenty_changes():
    assert is_change_only(regular_series(np.arange(21)))


def test_automatic_change_only_detection_for_irregular_sampling():
    analysis = analyze_sampling(burst_series())
    assert analysis.frequency == pd.Timedelta("1s")
    assert analysis.frequency_source == "auto"
    assert not analysis.regular_sampling
    assert analysis.change_only
    assert analysis.typical_pause == pd.Timedelta("5min")


def test_irregular_sampling_can_also_be_non_change_only():
    series = burst_series(np.random.default_rng(42).normal(size=60))
    analysis = analyze_sampling(series)
    assert not analysis.regular_sampling
    assert not analysis.change_only


@pytest.mark.parametrize("source", ["provided", "metadata"])
def test_known_frequency_defines_expected_regularity_and_prevents_auto_change_only(source):
    series = burst_series()
    if source == "metadata":
        series.attrs = recording_series(dataset_frequency="1s").attrs
    analysis = analyze_sampling(series, data_frequency="1s" if source == "provided" else None)
    assert analysis.frequency_source == source
    assert analysis.regular_sampling
    assert not analysis.change_only


@pytest.mark.parametrize("frequency", [None, "1s"])
def test_explicit_change_only_overrides_regularity(frequency):
    analysis = analyze_sampling(
        regular_series(np.arange(30)), data_frequency=frequency, change_only=True
    )
    assert analysis.change_only
    assert not analysis.regular_sampling


def test_explicit_false_disables_change_only_detection():
    analysis = analyze_sampling(burst_series(), change_only=False)
    assert not analysis.change_only
    assert not analysis.regular_sampling


@pytest.mark.parametrize("values", [[], [1.0], [1.0, 2.0], [np.nan, np.inf, np.nan]])
def test_empty_short_and_invalid_series_follow_component_fallbacks(values):
    analysis = analyze_sampling(regular_series(values))
    assert analysis.frequency == (pd.Timedelta("1min") if len(values) >= 3 else None)
    assert analysis.regular_sampling
    assert not analysis.change_only


def test_frequency_uses_timestamps_of_invalid_measurements():
    series = regular_series([1.0, np.nan, "invalid", np.inf, 5.0])
    analysis = analyze_sampling(series)
    assert analysis.frequency == pd.Timedelta("1min")
    assert analysis.typical_pause == pd.Timedelta("1min")
    assert analysis.regular_sampling


def test_analysis_sorts_and_averages_duplicates_without_modifying_input():
    series = pd.Series(
        [3.0, 1.0, 2.0, 4.0],
        index=pd.to_datetime(
            ["2026-01-01 00:02", "2026-01-01 00:00", "2026-01-01 00:01", "2026-01-01 00:01"]
        ),
        name="signal",
    )
    series.attrs = {"custom": {"values": [1, 2]}}
    original = series.copy(deep=True)
    expected = analyze_sampling(regular_series([1.0, 3.0, 3.0]))
    assert analyze_sampling(series) == expected
    pd.testing.assert_series_equal(series, original)
    assert series.attrs == original.attrs


def test_timezone_aware_timestamps_use_elapsed_time_across_dst():
    series = pd.Series(
        np.arange(10),
        index=pd.date_range("2026-10-25", periods=10, freq="1h", tz="Europe/Berlin"),
    )
    analysis = analyze_sampling(series)
    assert analysis.frequency == pd.Timedelta("1h")
    assert analysis.regular_sampling


def test_datetime_string_index_is_supported():
    series = pd.Series(
        [1.0, 2.0, 3.0], index=["2026-01-01 00:00", "2026-01-01 00:01", "2026-01-01 00:02"]
    )
    assert analyze_sampling(series).frequency == pd.Timedelta("1min")


@pytest.mark.parametrize(
    ("series", "error", "message"),
    [
        ([1.0, 2.0], TypeError, "pd.Series"),
        (pd.Series([1.0, 2.0]), ValueError, "timestamps, not numbers"),
        (pd.Series([1.0], index=pd.DatetimeIndex([pd.NaT])), ValueError, "NaT"),
        (regular_series(["invalid", "values"]), ValueError, "must be numeric"),
    ],
)
def test_invalid_series_inputs(series, error, message):
    with pytest.raises(error, match=message):
        analyze_sampling(series)


def test_invalid_change_only_parameter():
    with pytest.raises(TypeError, match="change_only"):
        analyze_sampling(regular_series([1.0, 2.0]), change_only="true")


def test_typical_pause_uses_time_weighting():
    assert typical_pause(burst_series().index) == pd.Timedelta("5min")


def test_typical_pause_includes_utc_query_boundaries():
    timestamps = pd.date_range("2026-01-01 00:01", periods=3, freq="1min", tz="UTC")
    assert typical_pause(
        timestamps, pd.Timestamp("2026-01-01"), pd.Timestamp("2026-01-01 00:10")
    ) == pd.Timedelta("7min")


def test_analysis_reads_query_boundaries_from_metadata():
    series = pd.Series(
        [1.0, 2.0, 3.0], index=pd.date_range("2026-01-01 00:01", periods=3, freq="1min", tz="UTC")
    )
    series.attrs = copy.deepcopy(SERIES_METADATA_EXAMPLE)
    series.attrs["dataset_metadata"]["ref_interval_end_timestamp"] = "2026-01-01T00:10:00Z"
    assert analyze_sampling(series).typical_pause == pd.Timedelta("7min")


@pytest.mark.parametrize("count", [0, 1])
def test_typical_pause_without_intervals_is_unknown(count):
    assert typical_pause(regular_series(np.ones(count)).index) is None


@pytest.mark.parametrize("attached", [False, True])
@pytest.mark.parametrize(
    ("mode", "regular", "change_only", "frequency", "source", "heartbeat"),
    [
        (None, True, False, "5min", "metadata", None),
        ("periodic", True, False, "5min", "metadata", None),
        ("irregular", False, False, "5min", "metadata", None),
        ("on_change", False, True, "1s", "auto", "5min"),
    ],
)
def test_recording_mode_precedes_sampling_heuristics(
    attached, mode, regular, change_only, frequency, source, heartbeat
):
    series = burst_series()
    series.attrs = recording_series(metric_frequency="5min", recording_mode=mode).attrs
    if attached:
        assert attach_metadata(series) is not None

    analysis = analyze_sampling(series)

    assert analysis.regular_sampling is regular
    assert analysis.change_only is change_only
    assert analysis.frequency == pd.Timedelta(frequency)
    assert analysis.frequency_source == source
    assert analysis.heartbeat == (pd.Timedelta(heartbeat) if heartbeat else None)


def test_on_change_metadata_does_not_require_enough_values_for_a_heuristic():
    series = recording_series(metric_frequency="5min", recording_mode="on_change").iloc[:2]
    analysis = analyze_sampling(series)
    assert analysis.change_only
    assert not analysis.regular_sampling
    assert analysis.frequency is None
    assert analysis.frequency_source == "auto"
    assert analysis.heartbeat == pd.Timedelta("5min")


def test_on_change_dataset_frequency_is_heartbeat_not_sampling_interval():
    series = burst_series()
    series.attrs = recording_series(dataset_frequency="5min", recording_mode="on_change").attrs
    assert parse_frequency_from_metadata(series) == pd.Timedelta("5min")
    assert resolve_data_frequency(series, series.index) == (pd.Timedelta("1s"), "auto")
    analysis = analyze_sampling(series)
    assert analysis.heartbeat == pd.Timedelta("5min")
    assert analysis.frequency == pd.Timedelta("1s")


def test_explicit_sampling_interval_keeps_on_change_heartbeat_separate():
    series = recording_series(metric_frequency="5min", recording_mode="on_change")
    analysis = analyze_sampling(series, data_frequency="30s")
    assert analysis.frequency == pd.Timedelta("30s")
    assert analysis.frequency_source == "provided"
    assert analysis.heartbeat == pd.Timedelta("5min")
    assert analysis.change_only
    assert not analysis.regular_sampling


@pytest.mark.parametrize(("mode", "override"), [("periodic", True), ("on_change", False)])
def test_explicit_change_only_overrides_recording_metadata(mode, override):
    series = recording_series(metric_frequency="5min", recording_mode=mode)
    analysis = analyze_sampling(series, change_only=override)
    assert analysis.change_only is override
    assert not analysis.regular_sampling


def test_explicit_interval_does_not_turn_irregular_metadata_into_periodic_sampling():
    series = burst_series()
    series.attrs = recording_series(recording_mode="irregular").attrs
    analysis = analyze_sampling(series, data_frequency="1s")
    assert analysis.frequency == pd.Timedelta("1s")
    assert analysis.frequency_source == "provided"
    assert not analysis.regular_sampling
    assert not analysis.change_only
