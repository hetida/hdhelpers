"""How the values of the metrics are recorded and how they should be aggregated by default

The frequency of the recorded values of a metric falls back as a whole: If the metric has a
"data_frequency", it applies together with the metric's "data_frequency_offset" and
"data_frequency_timezone". Otherwise "ref_data_frequency" of the dataset metadata applies
together with "ref_data_frequency_offset" and "ref_data_frequency_timezone".
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, cast

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


@dataclass(frozen=True)
class Recording:
    """How the values of a metric are recorded, as given in its metadata

    The fields mean the following:

    Attributes:
        recording_mode (str | None): "periodic": one value per interval of data_frequency, timestamped with the start of the interval. A missing value is a gap. "on_change": a value is recorded when it changes by more than the deadband of its value dimension and holds until the next one. Missing timestamps are no gaps. "irregular": values at arbitrary points in time. None if unknown.
        data_frequency (str | None): Frequency as Pandas date offset alias or timedelta string, e.g. "15min", "1D" or "1MS". For "on_change", the interval after which the value is recorded again at the latest, also without a change (heartbeat).
        data_frequency_offset (str | None): Timedelta string by which the intervals of data_frequency are shifted, e.g. "5min". None means 0.
        data_frequency_timezone (str | None): Time zone the intervals of data_frequency are aligned to, e.g. "Europe/Berlin". None means UTC.
        recording_aggregation_method (str | None): Only for "periodic": the method each value aggregates its interval with, e.g. "MEAN" or "MAX". None if the values are samples, e.g. the value holding at the timestamp.

    data_frequency_offset and data_frequency_timezone belong to data_frequency: They are None
    if no data_frequency applies.
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
