"""Reading metadata of the conventions, with the fallbacks of the conventions

The methods of MetadataReading are available on the root models of the conventions
(SeriesMetadata, SingleTSFrameMetadata, MultiTSFrameMetadata). They resolve the fallbacks:

- Information of a value dimension, e.g. its unit: Each field of a chain, e.g. display_name and
  then name, is looked up on the value dimension, for the value dimension "value" on the metric,
  then on the shared value dimension of the column (value_dimensions_shared), before the next
  field is tried. With include_inherited, the properties the metric inherits are the last resort
  for the value dimension "value".
- Information of a metric: the metric, its value dimension "value", the shared value dimension
  "value", with include_inherited finally the properties the metric inherits.
- Default time zone: the one of the metric, otherwise the one of the dataset metadata.
- Recording: the frequency of the metric together with its offset and time zone, otherwise the
  ones of the dataset metadata (ref_data_frequency etc.), always as a whole.
- Default aggregation method: the one of the metric, with AVG as MEAN, otherwise LAST for
  boolean and string values and MEAN for all others.

Fields can be given as dotted paths, e.g. "inherited.site". Information which is null counts as
missing. For a metric without metadata, information is None, apart from the fallbacks to the
dataset metadata.

For SERIES and SINGLETSFRAME metadata, the metric_id can be omitted, which refers to their single
metric. MULTITSFRAME metadata requires it.
"""

import datetime
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from functools import cached_property
from typing import TYPE_CHECKING, Any, ClassVar, Literal

from pydantic import BaseModel

if TYPE_CHECKING:
    from hdhelpers.metadata.conventions import (
        MetricMetadata,
        SharedValueDimensionMetadata,
        ValueDimensionMetadata,
        _DatasetMetadataBase,
    )

DISPLAY_NAME_FIELDS = ("display_name", "name")
SHORT_DISPLAY_NAME_FIELDS = ("short_display_name", *DISPLAY_NAME_FIELDS)

# default aggregation method of metrics without one by the data type of their values
_DEFAULT_AGGREGATION_METHOD_BY_VALUE_DATA_TYPE = {"boolean": "LAST", "string": "LAST"}
_DEFAULT_AGGREGATION_METHOD = "MEAN"
_AGGREGATION_METHOD_ALIASES = {"AVG": "MEAN"}

_MISSING = object()


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
    """  # noqa: E501

    recording_mode: str | None = None
    data_frequency: str | None = None
    data_frequency_offset: str | None = None
    data_frequency_timezone: str | None = None
    recording_aggregation_method: str | None = None


_Frequency = tuple[str | None, str | None, str | None]


def lookup(obj: Any, path: str) -> Any:
    """A field, extra field or dotted path of fields of a model or mapping, None if missing

    Members of enums are given as their values, e.g. "MEAN" for AggregationMethod.MEAN, as in
    the JSON form of the metadata.
    """
    for key in path.split("."):
        obj = _field(obj, key)
        if obj is None:
            return None
    return _plain(obj)


def id_of(metric: "MetricMetadata", metric_key: str) -> Any:
    """The id of a metric: its field named metric_key, which may contain dots, None if missing"""
    return _plain(_field(metric, metric_key))


def _field(obj: Any, key: str) -> Any:
    """A field or extra field of a model or a key of a mapping, None if missing"""
    if isinstance(obj, BaseModel):
        # __dict__ holds the fields, without warning about deprecated ones like getattr
        value = obj.__dict__.get(key, _MISSING)
        return (obj.__pydantic_extra__ or {}).get(key) if value is _MISSING else value
    if isinstance(obj, Mapping):
        return obj.get(key)
    return None


def _plain(value: Any) -> Any:
    """The value of an enum member, e.g. "MEAN" instead of AggregationMethod.MEAN"""
    return value.value if isinstance(value, Enum) else value


def _non_empty(value: Any) -> str | None:
    value = _plain(value)
    return value if isinstance(value, str) and value != "" else None


def _frequency(obj: Any, fields: tuple[str, str, str]) -> _Frequency:
    """Frequency, offset and time zone of obj, all None if it has no frequency"""
    frequency, offset, timezone = (_non_empty(lookup(obj, field)) for field in fields)
    return (None, None, None) if frequency is None else (frequency, offset, timezone)


def _value_dimension_info(
    fields: tuple[str, ...],
    metric: "MetricMetadata",
    value_dimensions: Mapping[str, "ValueDimensionMetadata"],
    shared: Mapping[str, "SharedValueDimensionMetadata"],
    column: str,
    include_inherited: bool,
) -> Any:
    value_dimension = value_dimensions.get(column)
    shared_value_dimension = shared.get(column)
    for field in fields:
        info = lookup(value_dimension, field)
        if info is None and column == "value":
            info = lookup(metric, field)
        if info is None:
            info = lookup(shared_value_dimension, field)
        if info is not None:
            return info
    if include_inherited and column == "value" and metric.inherited is not None:
        for field in fields:
            info = lookup(metric.inherited, field)
            if info is not None:
                return info
    return None


def _by_column(
    value_dimensions: "Sequence[ValueDimensionMetadata] | Sequence[SharedValueDimensionMetadata]",
) -> dict[str, Any]:
    return {value_dimension.column: value_dimension for value_dimension in value_dimensions}


def _fields(fields: str | Sequence[str]) -> tuple[str, ...]:
    return (fields,) if isinstance(fields, str) else tuple(fields)


class MetadataReading:
    """Lookups with the fallbacks of the conventions, see the module docstring"""

    if TYPE_CHECKING:
        dataset_metadata: _DatasetMetadataBase
        metrics: tuple[MetricMetadata, ...]
        value_dimensions_shared: tuple[SharedValueDimensionMetadata, ...] | None
        _data_type: ClassVar[Literal["SERIES", "SINGLETSFRAME", "MULTITSFRAME"]]

    # metrics

    def metric_ids(self) -> list[str]:
        """The ids of the metrics, i.e. their values of the field named by the metric key"""
        return list(self._metrics_by_id)

    def metric(self, metric_id: str | None = None) -> "MetricMetadata":
        """The metadata of a metric, KeyError if there is none"""
        metric = self._metric_or_none(metric_id)
        if metric is None:
            raise KeyError(metric_id)
        return metric

    @cached_property
    def _metrics_by_id(self) -> "dict[str, MetricMetadata]":
        """The metrics by id, built on first use

        Cached in __dict__ apart from the fields, which pydantic ignores when comparing models:
        Reading must not change the equality, since pandas keeps only equal attrs, e.g. on concat.
        """
        metric_key = self.dataset_metadata.metric_key
        return {id_of(metric, metric_key): metric for metric in self.metrics}

    def _metric_or_none(self, metric_id: str | None) -> "MetricMetadata | None":
        if metric_id is None:
            if self._data_type == "MULTITSFRAME":
                raise TypeError("The metric_id is required for MULTITSFRAME metadata.")
            return self.metrics[0]
        return self._metrics_by_id.get(metric_id)

    def _shared_by_column(self) -> "dict[str, SharedValueDimensionMetadata]":
        return _by_column(self.value_dimensions_shared or ())

    # information of value dimensions

    def value_dimension_info(
        self,
        fields: str | Sequence[str],
        metric_id: str | None = None,
        column: str = "value",
        *,
        include_inherited: bool = False,
    ) -> Any:
        """Information of a value dimension, trying the fields in turn"""
        metric = self._metric_or_none(metric_id)
        if metric is None:
            return None
        return _value_dimension_info(
            _fields(fields),
            metric,
            _by_column(metric.value_dimensions),
            self._shared_by_column(),
            column,
            include_inherited,
        )

    def value_dimension_infos(
        self, fields: str | Sequence[str], *, include_inherited: bool = False
    ) -> dict[str, dict[str, Any]]:
        """Information of the value dimensions by column by metric

        The value dimensions of a metric are its own ones, "value" and the shared ones.
        """
        fields = _fields(fields)
        shared = self._shared_by_column()
        result = {}
        for metric_id, metric in self._metrics_by_id.items():
            value_dimensions = _by_column(metric.value_dimensions)
            columns = dict.fromkeys([*shared, "value", *value_dimensions])
            result[metric_id] = {
                column: _value_dimension_info(
                    fields, metric, value_dimensions, shared, column, include_inherited
                )
                for column in columns
            }
        return result

    def unit(
        self,
        metric_id: str | None = None,
        column: str = "value",
        *,
        include_inherited: bool = False,
    ) -> str | None:
        return self.value_dimension_info(  # type: ignore[no-any-return]
            "unit", metric_id, column, include_inherited=include_inherited
        )

    def units(self, *, include_inherited: bool = False) -> dict[str, dict[str, str | None]]:
        return self.value_dimension_infos("unit", include_inherited=include_inherited)

    def measurement(
        self,
        metric_id: str | None = None,
        column: str = "value",
        *,
        include_inherited: bool = False,
    ) -> str | None:
        return self.value_dimension_info(  # type: ignore[no-any-return]
            "measurement", metric_id, column, include_inherited=include_inherited
        )

    def measurements(self, *, include_inherited: bool = False) -> dict[str, dict[str, str | None]]:
        return self.value_dimension_infos("measurement", include_inherited=include_inherited)

    def name(
        self,
        metric_id: str | None = None,
        column: str = "value",
        *,
        include_inherited: bool = False,
    ) -> str | None:
        return self.value_dimension_info(  # type: ignore[no-any-return]
            "name", metric_id, column, include_inherited=include_inherited
        )

    def names(self, *, include_inherited: bool = False) -> dict[str, dict[str, str | None]]:
        return self.value_dimension_infos("name", include_inherited=include_inherited)

    def display_name(
        self,
        metric_id: str | None = None,
        column: str = "value",
        *,
        include_inherited: bool = False,
    ) -> str | None:
        """The display name, falling back to the name"""
        return self.value_dimension_info(  # type: ignore[no-any-return]
            DISPLAY_NAME_FIELDS, metric_id, column, include_inherited=include_inherited
        )

    def display_names(self, *, include_inherited: bool = False) -> dict[str, dict[str, str | None]]:
        return self.value_dimension_infos(DISPLAY_NAME_FIELDS, include_inherited=include_inherited)

    def short_display_name(
        self,
        metric_id: str | None = None,
        column: str = "value",
        *,
        include_inherited: bool = False,
    ) -> str | None:
        """The short display name, falling back to the display name and the name"""
        return self.value_dimension_info(  # type: ignore[no-any-return]
            SHORT_DISPLAY_NAME_FIELDS, metric_id, column, include_inherited=include_inherited
        )

    def short_display_names(
        self, *, include_inherited: bool = False
    ) -> dict[str, dict[str, str | None]]:
        return self.value_dimension_infos(
            SHORT_DISPLAY_NAME_FIELDS, include_inherited=include_inherited
        )

    # information of metrics

    def metric_info(
        self, field: str, metric_id: str | None = None, *, include_inherited: bool = True
    ) -> Any:
        """Information of a metric, see the module docstring for the fallbacks"""
        metric = self._metric_or_none(metric_id)
        if metric is None:
            return None
        return self._metric_info(field, metric, self._shared_by_column(), include_inherited)

    def metric_infos(self, field: str, *, include_inherited: bool = True) -> dict[str, Any]:
        shared = self._shared_by_column()
        return {
            metric_id: self._metric_info(field, metric, shared, include_inherited)
            for metric_id, metric in self._metrics_by_id.items()
        }

    @staticmethod
    def _metric_info(
        field: str,
        metric: "MetricMetadata",
        shared: Mapping[str, "SharedValueDimensionMetadata"],
        include_inherited: bool,
    ) -> Any:
        info = lookup(metric, field)
        if info is None:
            info = lookup(_by_column(metric.value_dimensions).get("value"), field)
        if info is None:
            info = lookup(shared.get("value"), field)
        if info is None and include_inherited:
            info = lookup(metric.inherited, field)
        return info

    # time zones, recording, aggregation and the queried interval

    def default_timezone(self, metric_id: str | None = None) -> str | None:
        """The default time zone of the metric, otherwise the one of the dataset metadata"""
        metric = self._metric_or_none(metric_id)
        own = None if metric is None else _non_empty(metric.default_timezone)
        return own or dataset_default_timezone(self)

    def default_timezones(self) -> dict[str, str | None]:
        return {metric_id: self.default_timezone(metric_id) for metric_id in self._metrics_by_id}

    def recording(self, metric_id: str | None = None) -> Recording:
        """How the values of the metric are recorded

        The frequency with its offset and time zone falls back to the ones of the dataset
        metadata as a whole.
        """
        dataset_frequency = _dataset_frequency(self)
        metric = self._metric_or_none(metric_id)
        if metric is None:
            return Recording(None, *dataset_frequency, None)
        own_frequency = _frequency(
            metric, ("data_frequency", "data_frequency_offset", "data_frequency_timezone")
        )
        return Recording(
            _non_empty(metric.recording_mode),
            *(own_frequency if own_frequency[0] is not None else dataset_frequency),
            _non_empty(metric.recording_aggregation_method),
        )

    def recordings(self) -> dict[str, Recording]:
        return {metric_id: self.recording(metric_id) for metric_id in self._metrics_by_id}

    def default_aggregation_method(self, metric_id: str | None = None) -> str:
        """The default aggregation method of the metric, see the module docstring"""
        metric = self._metric_or_none(metric_id)
        if metric is None:
            return _DEFAULT_AGGREGATION_METHOD
        own_method = _non_empty(metric.default_aggregation_method)
        if own_method is not None:
            return _AGGREGATION_METHOD_ALIASES.get(own_method, own_method)
        value_data_type = _plain(
            _value_dimension_info(
                ("value_data_type",),
                metric,
                _by_column(metric.value_dimensions),
                self._shared_by_column(),
                "value",
                include_inherited=False,
            )
        )
        return _DEFAULT_AGGREGATION_METHOD_BY_VALUE_DATA_TYPE.get(
            value_data_type, _DEFAULT_AGGREGATION_METHOD
        )

    def default_aggregation_methods(self) -> dict[str, str]:
        return {
            metric_id: self.default_aggregation_method(metric_id)
            for metric_id in self._metrics_by_id
        }

    def queried_interval(self) -> tuple[datetime.datetime | None, datetime.datetime | None]:
        """Start and end of the queried interval (the ref interval), None if missing"""
        return (
            _datetime(self.dataset_metadata.ref_interval_start_timestamp),
            _datetime(self.dataset_metadata.ref_interval_end_timestamp),
        )


def _datetime(timestamp: str | None) -> datetime.datetime | None:
    return None if timestamp is None else datetime.datetime.fromisoformat(timestamp)


def _dataset_frequency(meta: MetadataReading) -> _Frequency:
    return _frequency(
        meta.dataset_metadata,
        ("ref_data_frequency", "ref_data_frequency_offset", "ref_data_frequency_timezone"),
    )


def dataset_default_timezone(meta: MetadataReading) -> str | None:
    """The default time zone of the dataset metadata, which applies to metrics without one"""
    return _non_empty(meta.dataset_metadata.default_timezone)


def dataset_recording(meta: MetadataReading) -> Recording:
    """The recording of a metric without metadata: only the frequency of the dataset metadata"""
    return Recording(None, *_dataset_frequency(meta), None)
