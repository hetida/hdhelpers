"""Metadata conventions for timeseries data

The models in this module specify the hetida designer metadata conventions for the metadata
(attrs) of SERIES, SINGLETSFRAME and MULTITSFRAME objects, one model per data type. See the user
guide page on attached metadata for an introduction.

The conventions are strict: Metadata adhering to them provides the required fields, possibly as
null if the information is unknown, e.g. the unit of a value dimension. Consumers like components
should nevertheless cope with missing metadata, since validation of metadata received from
adapters is optional.

The models document the request body of the hetida designer backend endpoint for checking
metadata. Hence they occur as JSON Schemas in the openapi.json of the backend, so that third party
projects, e.g. adapters providing or receiving such metadata, can validate against them.
Additional fields are allowed at every level. The models are immutable, see ConventionModel.

check_metadata_conventions additionally checks the rules which JSON Schema cannot express,
optionally against the actual data.
"""

import datetime
import difflib
import json
import math
import re
from collections import Counter
from collections.abc import Mapping
from enum import StrEnum
from functools import cache, lru_cache
from importlib import resources
from typing import Annotated, Any, ClassVar, Literal, NoReturn, Self

import pandas as pd
from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    GetJsonSchemaHandler,
    ModelWrapValidatorHandler,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    ValidationError,
    ValidationInfo,
    model_validator,
)
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, PydanticCustomError

from hdhelpers.metadata._reading import MetadataReading, lookup

TimeseriesDataType = Literal["SERIES", "SINGLETSFRAME", "MULTITSFRAME"]


class IntervalType(StrEnum):
    """Which boundaries belong to a time interval

    closed: both, open: none, left_closed / right_open: only the start,
    right_closed / left_open: only the end.
    """

    CLOSED = "closed"
    LEFT_CLOSED = "left_closed"
    RIGHT_CLOSED = "right_closed"
    OPEN = "open"
    LEFT_OPEN = "left_open"
    RIGHT_OPEN = "right_open"


# [0-9] instead of \d, since \d also matches non-ASCII digits in some regex dialects
UTC_TIMESTAMP_PATTERN = (
    r"^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])"
    r"T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](\.[0-9]+)?(Z|\+00:00)$"
)


def _check_point_in_time(timestamp: str) -> str:
    """Reject timestamps of the pattern which are no actual points in time, e.g. February 30"""
    try:
        datetime.datetime.fromisoformat(timestamp)
    except ValueError as e:
        raise ValueError(f"{timestamp!r} is not an actual point in time: {e}.") from e
    return timestamp


def _utc_isoformat(value: Any) -> Any:
    """A datetime with UTC offset 0 as isoformat string, so that producers can pass datetimes"""
    if not isinstance(value, datetime.datetime):
        return value
    if value.utcoffset() is None:
        raise ValueError(f"{value!r} is naive, but needs to be in UTC.")
    if value.utcoffset() != datetime.timedelta(0):
        raise ValueError(f"{value!r} is not in UTC.")
    return value.isoformat()


# The pattern specifies the format in the JSON Schema, which cannot express that the date and
# time must exist. Pydantic's datetime type is not used, since it accepts further formats and
# offsets, so that the check would be more lenient than the published JSON Schema.
UtcTimestamp = Annotated[
    str,
    Field(pattern=UTC_TIMESTAMP_PATTERN, json_schema_extra={"format": "date-time"}),
    AfterValidator(_check_point_in_time),
    # last, so that it runs first and the JSON Schema keeps the pattern
    BeforeValidator(_utc_isoformat),
]


class AggregationMethod(StrEnum):
    """How a timeseries should be aggregated by default, e.g. in coarser intervals

    AVG is an alias of MEAN.
    """

    MEAN = "MEAN"
    AVG = "AVG"
    MEDIAN = "MEDIAN"
    SUM = "SUM"
    MIN = "MIN"
    MAX = "MAX"
    FIRST = "FIRST"
    LAST = "LAST"
    COUNT = "COUNT"


class ValueDataType(StrEnum):
    """Data type of the values of a value dimension"""

    FLOAT = "float"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    STRING = "string"


class RecordingMode(StrEnum):
    """When the values of a timeseries are recorded

    periodic: one value per interval of data_frequency, timestamped with the start of the
    interval. A missing value is a gap.
    on_change: a value is recorded when it changes (by more than the deadband of its value
    dimension) and holds until the next one. Missing timestamps are no gaps, as long as
    data_frequency (the heartbeat) is not exceeded.
    irregular: values at arbitrary points in time.
    """

    PERIODIC = "periodic"
    ON_CHANGE = "on_change"
    IRREGULAR = "irregular"


_FREQUENCY_FORMAT = 'as Pandas date offset alias or timedelta string, e.g. "15min" or "1D"'
_OFFSET_DESCRIPTION = (
    "Offset of the timestamps against the starts of the intervals of {frequency} (see"
    ' {timezone}) as timedelta string, e.g. "4min": not negative and smaller than {frequency}. 0'
    " if missing or null. Requires {frequency}."
)

_TIMEZONE_FORMAT = (
    'as IANA time zone name like "Europe/Berlin" or "UTC" (preferred, since it respects daylight'
    ' saving time) or as fixed UTC offset like "+02:00"'
)

_ALIGNMENT_DESCRIPTION = (
    "Time zone the intervals of {frequency} are aligned to, "
    + _TIMEZONE_FORMAT
    + ". Without it, the intervals start at the multiples of {frequency} since"
    " 1970-01-01T00:00:00Z. With it, for a {frequency} shorter than a day, the intervals restart"
    " at each local midnight: They start at local midnight plus multiples of {frequency}, and the"
    " last interval of a day ends at the next local midnight, so it may be shorter, e.g. on the"
    " day of a daylight saving time change. For a {frequency} of a day or longer, the intervals"
    " follow the calendar of the time zone, e.g. days from local midnight to local midnight. The"
    " offset shifts the intervals in both cases. Requires {frequency}."
)
_TIMEZONE_PURPOSE = (
    " Components evaluating the timeseries in calendar intervals use it, e.g. a report"
    " aggregating days, which start at midnight of this time zone, so the results differ between"
    " time zones. This is not the time zone timestamps are displayed in: That is the plot target"
    " timezone of the execution context, which depends on the viewer, while this time zone belongs"
    " to the data, e.g. the time zone of the plant."
)


def _immutable(self: Any, *args: Any, **kwargs: Any) -> NoReturn:
    raise TypeError(f"{type(self).__name__} is immutable")


class FrozenDict(dict[str, Any]):
    """A dict which cannot be changed

    Holds dict values of extra fields of the convention models, since the models are shared
    between pandas objects instead of being copied. Use it as a read-only mapping, not as a dict:
    The builtin frozendict of Python 3.15, which is planned to replace it, is no dict subclass.
    """

    __slots__ = ()
    __setitem__ = __delitem__ = __ior__ = _immutable  # type: ignore[assignment]
    clear = pop = popitem = setdefault = update = _immutable  # type: ignore[assignment]

    def __copy__(self) -> Self:
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        return self

    def __reduce__(self) -> tuple[Any, ...]:
        return (FrozenDict, (dict(self),))


def _freeze(value: Any) -> Any:
    """A JSON value with dicts and lists as FrozenDicts and tuples, recursively"""
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("Keys of JSON objects must be strings.")
        return FrozenDict({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list | tuple):
        return tuple(_freeze(item) for item in value)
    if (
        value is None
        or isinstance(value, str | int)
        or (isinstance(value, float) and math.isfinite(value))
    ):
        return value
    raise ValueError(f"{value!r} is not a JSON value.")


_JsonFloat = Annotated[StrictFloat, Field(allow_inf_nan=False)]

# Scalars are validated within pydantic-core. Only dicts and lists need Python for freezing them.
_FrozenValue = Annotated[
    StrictStr
    | StrictInt
    | _JsonFloat
    | StrictBool
    | None
    | Annotated[Any, AfterValidator(_freeze)],
    Field(union_mode="left_to_right"),
]


def optional(default: Any = None, **kwargs: Any) -> Any:
    """Field for an optional value, left out of dumps while it is None or the default"""
    return Field(default, exclude_if=lambda value: value is None or value == default, **kwargs)


def _item_count(min_length: int, max_length: int | None = None) -> BeforeValidator:
    """Check the number of items before validating them

    Pydantic counts the items of a tuple after validating them, so that an invalid item would
    also be reported as missing. The JSON Schema states the counts via json_schema_extra.
    """

    def items(count: int) -> str:
        return f"{count} item" if count == 1 else f"{count} items"

    def check(value: Any) -> Any:
        if isinstance(value, list | tuple):
            if len(value) < min_length:
                raise PydanticCustomError(
                    "too_short", f"Should have at least {items(min_length)}, not {len(value)}"
                )
            if max_length is not None and len(value) > max_length:
                raise PydanticCustomError(
                    "too_long", f"Should have at most {items(max_length)}, not {len(value)}"
                )
            # a tuple, since strict validation after a before validator rejects lists
            return tuple(value)
        return value

    return BeforeValidator(check)


class ConventionModel(BaseModel):
    """Base of the models of the metadata conventions

    The models are immutable, including the values of extra fields, so that pandas objects can
    share them instead of copying them: pandas deep-copies the attrs of an object for (almost)
    every object derived from it. A changed version of a model is a new model, which shares all
    unchanged parts with the original.
    """

    # Validation is lax, so that Python input may contain lists for the tuples. Fields whose type
    # lax validation would coerce (bool, int, float) use the strict types instead, so that the
    # results equal strict validation of JSON input.
    model_config = ConfigDict(extra="allow", frozen=True)
    __pydantic_extra__: dict[str, _FrozenValue]

    def __deepcopy__(self, memo: dict[int, Any] | None = None) -> Self:
        return self

    def model_copy(self, *, update: Mapping[str, Any] | None = None, deep: bool = False) -> Self:
        """Copy with the given fields replaced, without validating them

        Always shallow, since the model is immutable. A deep copy would apply the update to the
        original, since __deepcopy__ returns the original.
        """
        return super().model_copy(update=update, deep=False)

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        json_schema = handler(core_schema)
        # Any JSON value is allowed in extra fields, as without the typed __pydantic_extra__
        handler.resolve_ref_schema(json_schema)["additionalProperties"] = True
        return json_schema


class SharedValueDimensionMetadata(ConventionModel):
    """Metadata of a value dimension shared by all metrics

    Every column of a MULTITSFRAME besides "timestamp" and "metric" and every column of a
    SINGLETSFRAME besides "timestamp" defines a value dimension for each metric. A SERIES has
    exactly one value dimension, which is "value".
    """

    column: str = Field(
        ...,
        description="The actual column name in the MULTITSFRAME or SINGLETSFRAME, connecting the"
        ' value dimension to its column. "value" for a SERIES.',
    )
    name: str | None = optional(
        description='Name of the value dimension, e.g. "temperature". May equal column.'
    )
    display_name: str | None = optional(
        description="A shorter name for labels, captions or plot titles. Falls back to name.",
    )
    short_display_name: str | None = optional(
        description="A short name for legends in plots. Falls back to display_name."
    )
    description: str | None = optional(
        description="A description. Should be considered empty if missing."
    )
    unit: str | None = optional(
        description='Unit of the values, e.g. "°C" or "m/s", "" for dimensionless quantities',
    )
    measurement: str | None = optional(description='The measured quantity, e.g. "temperature"')
    value_data_type: ValueDataType | None = optional(description="Data type of the values")
    deadband: StrictFloat | None = optional(
        ge=0,
        allow_inf_nan=False,
        description="For a metric with recording_mode on_change: the change of the values, in"
        " their unit, which has to be exceeded for a value to be recorded. 0 records every"
        " change.",
    )
    decimals: StrictInt | None = optional(
        ge=0,
        description="Number of decimal places numeric values should be displayed with, in their"
        " unit, e.g. 2 for 12.35. Only affects how values are displayed, e.g. in tables, tooltips"
        " or reports; the values themselves are not rounded. Up to the consumer if missing or"
        " null.",
    )


class ValueDimensionMetadata(SharedValueDimensionMetadata):
    """Metadata of a value dimension of a metric

    Every column of a MULTITSFRAME besides "timestamp" and "metric" and every column of a
    SINGLETSFRAME besides "timestamp" defines a value dimension for each metric. A SERIES has
    exactly one value dimension, which is "value". Each metric provides an entry for each of its
    value dimensions.
    """

    unit: str | None = Field(
        ...,
        description='Unit of the values, e.g. "°C" or "m/s". "" for dimensionless quantities, null'
        " if unknown.",
    )
    measurement: str | None = Field(
        ..., description='The measured quantity, e.g. "temperature". Null if unknown.'
    )


class InheritedMetricMetadata(ConventionModel):
    """Properties a metric inherits from objects higher up in a hierarchy

    Arbitrary fields, e.g. the latitude of the plant a sensor belongs to. Typically the deepest
    occurrence in the hierarchy wins. Should not contain the fields the conventions define for
    metrics and value dimensions, like "name", "id" or "unit": Consumers only use inherited
    properties as last resort and not for information describing the metric itself, like its
    unit or names.

    The values should have the JSON type matching their meaning: numbers as numbers, booleans as
    booleans and points in time as UTC isoformat strings, not e.g. a number as string.

    E.g. the hetida platform provides the effective property values of a signal here, keyed by
    property label: its own values, otherwise the value of the nearest asset above it having one.
    """


class MetricCommentReply(ConventionModel):
    """A reply to a comment attached to a metric"""

    id: str | None = optional(description="Id of the reply, e.g. a UUID")
    created_at: UtcTimestamp | None = optional(description="When the reply was created")
    edited_at: UtcTimestamp | None = optional(
        description="When the reply was last edited. Null or missing if never edited."
    )
    content: str | None = optional(description="Free text of the reply")
    username: str | None = optional(description="Username of the author of the reply")


class MetricComment(ConventionModel):
    """A comment attached to a metric, describing a time range of its timeseries data

    E.g. the hetida platform provides the comments on a signal whose time range overlaps the
    queried interval and which existed at query time, newest first.

    Start and end of the time range must be provided together. They are equal for a comment on a
    single point in time.
    """

    id: str | None = optional(description="Id of the comment, e.g. a UUID")
    start_date: UtcTimestamp | None = optional(
        description="Start of the time range the comment refers to"
    )
    end_date: UtcTimestamp | None = optional(
        description="End of the time range the comment refers to"
    )
    created_at: UtcTimestamp | None = optional(description="When the comment was created")
    edited_at: UtcTimestamp | None = optional(
        description="When the comment was last edited. Null or missing if never edited."
    )
    content: str | None = optional(description="Free text of the comment")
    username: str | None = optional(description="Username of the author of the comment")
    tags: tuple[str, ...] | None = optional(description="Free text tags classifying the comment")
    replies: tuple[MetricCommentReply, ...] | None = optional(
        description="Replies to the comment, oldest first"
    )


class MetricMetadata(ConventionModel):
    """Metadata of a metric, i.e. of a single, possibly multidimensional timeseries

    A metric is identified by its field named by dataset_metadata.metric_key, whose values occur
    in the metric column of a MULTITSFRAME. Every metric must have this field as a string,
    unique among the metrics.
    """

    id: str = Field(
        ...,
        description="Id of the metric, also if another field identifies the metric in the data"
        " via dataset_metadata.metric_key. E.g. the hetida platform provides the signal id here.",
    )
    name: str = Field(..., description="Long name of the metric")
    display_name: str | None = optional(
        description="A shorter name for labels, captions or plot titles"
    )
    short_display_name: str | None = optional(description="A short name for legends in plots")
    description: str | None = optional(description="A one sentence description")
    external_id: str | None = optional(
        description="Unique id / key in external source systems. Often used to identify the"
        " metric in the metric column, i.e. as metric_key.",
    )
    signal_id: str | None = optional(description="Actual platform signal id")
    channel_id: str | None = optional(
        description="Actual platform channel id. Deprecated, since the platform calls channels"
        " signals now.",
        deprecated='Use "signal_id" instead.',
    )
    value_dimensions: Annotated[tuple[ValueDimensionMetadata, ...], _item_count(1)] = Field(
        ...,
        json_schema_extra={"minItems": 1},
        description="Metadata of the value dimensions of this metric: an entry for each value"
        ' column of the data, i.e. exactly the value dimension "value" for a SERIES. Each column'
        " may occur at most once.",
    )
    default_aggregation_method: AggregationMethod | None = optional(
        description="How the timeseries should be aggregated by default, e.g. when components"
        " plot or report it in coarser intervals. If missing or null: LAST if the value_data_type"
        ' of the value dimension "value" is boolean or string, otherwise MEAN. AVG is an alias'
        " of MEAN. E.g. the hetida platform provides the method it aggregates the signal with when"
        " bucketing it, for a signal group member the one configured for the member.",
    )
    default_timezone: str | None = optional(
        description="Time zone the timeseries should be evaluated in by default, "
        + _TIMEZONE_FORMAT
        + "."
        + _TIMEZONE_PURPOSE
        + " Falls back to dataset_metadata.default_timezone.",
    )
    path: tuple[str, ...] | None = optional(
        description="Location of the metric in the hierarchy of its source system: the names of"
        " the levels from the top down to the object the metric belongs to, without the metric"
        ' itself, e.g. ["Plant A", "Pickling Unit", "Influx"]. Corresponds to the breadcrumb'
        " path of the sources of generic REST adapters.",
    )
    origin: str | None = optional(
        description="Where the values come from, as free text of the source system, e.g."
        ' "OPC_UA", "MQTT" or "FORM" for values entered manually.',
    )
    recording_mode: RecordingMode | None = optional(
        description="When the values are recorded. Unknown if missing or null. periodic requires"
        " data_frequency (or dataset_metadata.ref_data_frequency).",
    )
    data_frequency: str | None = optional(
        description="Interval in which values of the metric are recorded "
        + _FREQUENCY_FORMAT
        + ": For recording_mode periodic the interval between subsequent values, for on_change"
        " the interval after which the value is recorded again at the latest, also without a"
        " change (heartbeat). Together with data_frequency_offset and data_frequency_timezone it"
        " takes precedence over ref_data_frequency, ref_data_frequency_offset and"
        " ref_data_frequency_timezone of the dataset metadata for this metric.",
    )
    data_frequency_offset: str | None = optional(
        description=_OFFSET_DESCRIPTION.format(
            frequency="data_frequency", timezone="data_frequency_timezone"
        ),
    )
    data_frequency_timezone: str | None = optional(
        description=_ALIGNMENT_DESCRIPTION.format(frequency="data_frequency")
    )
    recording_aggregation_method: AggregationMethod | None = optional(
        description="Only for recording_mode periodic: how each value aggregates the values of"
        " the interval [timestamp, timestamp + data_frequency), e.g. MEAN for an average or MAX"
        " for a maximum. Null or missing if the values are samples, e.g. the value holding at"
        " the timestamp.",
    )
    inherited: InheritedMetricMetadata | None = optional()
    comments: tuple[MetricComment, ...] | None = optional(
        description="Comments attached to the metric, describing situations in its timeseries data",
    )


class SignalGroupMetadata(ConventionModel):
    """A group of signals a dataset was read from

    E.g. the hetida platform provides the signal group a MULTITSFRAME was read from.
    """

    id: str | None = optional(description="Id of the signal group")
    name: str | None = optional(description="Name of the signal group")
    description: str | None = optional(description="Description of the signal group")


REF_INTERVAL_FIELDS = (
    "ref_interval_start_timestamp",
    "ref_interval_end_timestamp",
    "ref_interval_type",
)

# JSON Schema of the rule that the ref interval is required unless ref_dataset_discrete is true
_REF_INTERVAL_REQUIRED_SCHEMA: dict[str, Any] = {
    "if": {
        "properties": {"ref_dataset_discrete": {"const": True}},
        "required": ["ref_dataset_discrete"],
    },
    "else": {
        "required": list(REF_INTERVAL_FIELDS),
        "properties": {field: {"type": "string"} for field in REF_INTERVAL_FIELDS},
    },
}


class _DatasetMetadataBase(ConventionModel):
    model_config = ConfigDict(json_schema_extra=_REF_INTERVAL_REQUIRED_SCHEMA)

    metric_key: str = Field(
        ...,
        description="Which field of the metric objects under metrics identifies a metric, i.e."
        ' occurs in the metric column of a MULTITSFRAME, e.g. "id" or "external_id".',
    )
    queried_metrics: tuple[str, ...] = Field(
        ...,
        description="The requested metrics. Since not all queried metrics may have data in the"
        " queried interval, a metric may be missing in the data.",
    )
    signal_group: SignalGroupMetadata | None = optional()
    ref_dataset_discrete: StrictBool | None = optional(
        False,
        description="Whether the ref dataset should be considered as discrete, i.e. isolated"
        " datapoints instead of an interval. If true, the ref interval is not required.",
    )
    ref_interval_start_timestamp: UtcTimestamp | None = optional(
        description="Start of the queried time interval (ref interval) in UTC isoformat."
        " Required unless ref_dataset_discrete is true.",
    )
    ref_interval_end_timestamp: UtcTimestamp | None = optional(
        description="End of the queried time interval (ref interval) in UTC isoformat."
        " Required unless ref_dataset_discrete is true.",
    )
    ref_interval_type: IntervalType | None = optional(
        description="Type of the ref interval. Required unless ref_dataset_discrete is true.",
    )
    ref_data_frequency: str | None = optional(
        description="Frequency of the timeseries "
        + _FREQUENCY_FORMAT
        + ": the data_frequency of all metrics without their own, with the same meaning as"
        " there. Together with ref_data_frequency_offset and ref_data_frequency_timezone.",
    )
    ref_data_frequency_offset: str | None = optional(
        description=_OFFSET_DESCRIPTION.format(
            frequency="ref_data_frequency", timezone="ref_data_frequency_timezone"
        )
        + " Applies to all metrics without their own data_frequency.",
    )
    ref_data_frequency_timezone: str | None = optional(
        description=_ALIGNMENT_DESCRIPTION.format(frequency="ref_data_frequency")
        + " Applies to all metrics without their own data_frequency.",
    )
    query_timestamp: UtcTimestamp | None = optional(
        description="The point in time whose state of the data was delivered in UTC isoformat:"
        " Data stored, changed or invalidated later is not included. A source supporting it"
        " delivers the same data again when queried for this point in time, e.g. for"
        " reproducing an execution.",
    )
    default_aggregation_interval: str | None = optional(
        description="Interval to aggregate the timeseries to by default, e.g. when components"
        " plot or report them, "
        + _FREQUENCY_FORMAT
        + ". The metrics are aggregated with their default_aggregation_method. E.g. a hetida"
        " platform signal group is configured with such an interval.",
    )
    default_timezone: str | None = optional(
        description="Time zone the timeseries should be evaluated in by default, "
        + _TIMEZONE_FORMAT
        + "."
        + _TIMEZONE_PURPOSE
        + " Applies to all metrics without their own default_timezone.",
    )
    invalidation_interval_start: UtcTimestamp | None = optional(
        description="Start of an invalidation interval separate from the ref interval in UTC"
        " isoformat",
    )
    invalidation_interval_end: UtcTimestamp | None = optional(
        description="End of an invalidation interval separate from the ref interval in UTC"
        " isoformat",
    )
    invalidation_interval_type: IntervalType | None = optional(
        IntervalType.CLOSED, description="Type of the invalidation interval"
    )
    invalidate_dataset: StrictBool | None = optional(
        description="Whether existing data should be invalidated: in the invalidation interval if"
        " specified, otherwise in the ref interval. If neither is specified, a closed ref interval"
        " from the first to the last datapoint is inferred. Without datapoints no invalidation can"
        " occur then. What null means is up to the adapter.",
    )
    delete_invalidated: StrictBool | None = optional(
        description="Whether data to be invalidated should be deleted instead. What null means is"
        " up to the adapter. Adapters do not need to support deletion.",
    )
    invalidation_timestamp: UtcTimestamp | None = optional(
        description="Invalidation timestamp for all invalidated datapoints. If null, the"
        " execution_timestamp query parameter sent to generic REST adapters or, if that is not"
        " present either, the current time should be used.",
    )
    only_invalidate: StrictBool | None = optional(
        False,
        description="If true, existing data should only be invalidated and the new data should"
        " not be stored. Cannot be true if invalidate_dataset is false.",
    )
    new_data_invalidation_date: UtcTimestamp | None = optional(
        description="An invalidation date to be stored together with all new datapoints, i.e."
        " invalidating them in advance. Ignored if null.",
    )


class SingleMetricDatasetMetadata(_DatasetMetadataBase):
    """Metadata associated with a SERIES or SINGLETSFRAME as a whole

    E.g. the queried time interval or how existing data should be handled when the dataset is
    sent to an adapter. The fields concerning invalidation and deletion are only relevant for
    adapters actually supporting these operations, like the built-in SQL adapter. Other adapters
    may ignore them.

    Start and end of an interval must be provided together.
    """

    single_metric: str = Field(
        ..., description="The metric_key field value of the single metric under metrics."
    )


class MultiTSFrameDatasetMetadata(_DatasetMetadataBase):
    """Metadata associated with a MULTITSFRAME as a whole

    E.g. the queried time interval or how existing data should be handled when the dataset is
    sent to an adapter. The fields concerning invalidation and deletion are only relevant for
    adapters actually supporting these operations, like the built-in SQL adapter. Other adapters
    may ignore them.

    Start and end of an interval must be provided together.
    """

    single_metric: str | None = optional(
        description="If the MULTITSFRAME holds a single metric: its metric_key field value. Must"
        " not be set if more than one metric is present.",
    )


class _TimeseriesMetadataBase(MetadataReading, ConventionModel):
    """Base of the root models, the metadata of a SERIES, SINGLETSFRAME or MULTITSFRAME

    The methods of MetadataReading look up information with the fallbacks of the conventions.
    The with_* methods return changed versions, which share all unchanged parts with this one.
    """

    _data_type: ClassVar[TimeseriesDataType]

    value_dimensions_shared: tuple[SharedValueDimensionMetadata, ...] | None = optional(
        description="Metadata of value dimensions that have the same meaning for all metrics."
        " Consumers use it as fallback, but it does not replace the value dimensions of the"
        " metrics. Each column may occur at most once.",
    )

    @model_validator(mode="wrap")
    @classmethod
    def _conforms(
        cls, data: Any, handler: ModelWrapValidatorHandler[Self], info: ValidationInfo
    ) -> Self:
        """Reject metadata violating the rules of the conventions which JSON Schema cannot express

        check_metadata_conventions reports these errors itself, at their exact locations.
        """
        model = handler(data)
        if (info.context or {}).get(_SKIP_RULES) is True:
            return model
        errors = _rule_errors(data, model, cls._data_type)
        if len(errors) > 0:
            raise MetadataConventionError(errors)
        return model

    def model_copy(self, *, update: Mapping[str, Any] | None = None, deep: bool = False) -> Self:
        copied = super().model_copy(update=update, deep=deep)
        copied.__dict__.pop("_metrics_by_id", None)  # the metrics may differ
        return copied

    def _converted[T: "_TimeseriesMetadataBase"](self, model: type[T], **fields: Any) -> T:
        """The metadata as model with the given fields, keeping the extra fields"""
        return model.model_validate(self.__pydantic_extra__ | fields)

    def with_metric(self, metric_id: str | None = None, /, **changes: Any) -> Self:
        """A version with fields of a metric changed, the other metrics are shared

        The changed metric is validated, including the rules of the conventions which concern it.
        """
        old = self.metric(metric_id)
        new = type(old).model_validate(old.model_dump() | changes)
        errors = _metric_rule_errors(self, new)
        new_id = lookup(new, self.dataset_metadata.metric_key)
        if new_id != lookup(old, self.dataset_metadata.metric_key) and new_id in self.metric_ids():
            errors.append(_error("metrics", f'Metric "{new_id}" occurs more than once.'))
        if len(errors) > 0:
            raise MetadataConventionError(errors)
        return self.model_copy(
            update={"metrics": tuple(new if metric is old else metric for metric in self.metrics)}
        )

    def with_value_dimension(
        self, metric_id: str | None = None, column: str = "value", /, **changes: Any
    ) -> Self:
        """A version with fields of a value dimension of a metric changed, see with_metric"""
        metric = self.metric(metric_id)
        if column not in {value_dimension.column for value_dimension in metric.value_dimensions}:
            raise KeyError(column)
        return self.with_metric(
            metric_id,
            value_dimensions=tuple(
                value_dimension.model_dump() | changes
                if value_dimension.column == column
                else value_dimension
                for value_dimension in metric.value_dimensions
            ),
        )

    def with_dataset_metadata(self, **changes: Any) -> Self:
        """A version with fields of the dataset metadata changed, the metrics are shared

        Validated including all rules of the conventions, since the dataset metadata concerns
        all metrics.
        """
        old = self.dataset_metadata
        changed = self.model_copy(
            update={"dataset_metadata": type(old).model_validate(old.model_dump() | changes)}
        )
        errors = _rule_errors(None, changed, self._data_type)
        if len(errors) > 0:
            raise MetadataConventionError(errors)
        return changed


def _value_dimension(column: str, unit: str | None, measurement: str | None) -> dict[str, Any]:
    return {"column": column, "unit": unit, "measurement": measurement}


SERIES_METADATA_EXAMPLE: dict[str, Any] = {
    "dataset_metadata": {
        "metric_key": "id",
        "single_metric": "7ab8c419-8745-4714-b588-57c0c772cc95",
        "queried_metrics": ["7ab8c419-8745-4714-b588-57c0c772cc95"],
        "ref_interval_start_timestamp": "2026-01-01T00:00:00+00:00",
        "ref_interval_end_timestamp": "2026-01-02T00:00:00+00:00",
        "ref_interval_type": "right_open",
        "query_timestamp": "2026-01-02T00:05:00+00:00",
    },
    "metrics": [
        {
            "id": "7ab8c419-8745-4714-b588-57c0c772cc95",
            "name": "Water level north",
            "value_dimensions": [_value_dimension("value", "m", "level") | {"decimals": 2}],
            "default_aggregation_method": "MEAN",
            "default_timezone": "Europe/Berlin",
            "path": ["Waterworks North", "Gauge North"],
            "origin": "OPC_UA",
            "recording_mode": "periodic",
            "data_frequency": "15min",
            "recording_aggregation_method": "MEAN",
        }
    ],
}

SINGLETSFRAME_METADATA_EXAMPLE: dict[str, Any] = {
    "dataset_metadata": {
        "metric_key": "external_id",
        "single_metric": "abc.temp",
        "queried_metrics": ["abc.temp"],
        "ref_interval_start_timestamp": "2026-01-01T00:00:00+00:00",
        "ref_interval_end_timestamp": "2026-01-02T00:00:00+00:00",
        "ref_interval_type": "closed",
    },
    "metrics": [
        {
            "id": "3f2b1c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
            "external_id": "abc.temp",
            "name": "ABC temperature",
            "value_dimensions": [
                _value_dimension("value", "°C", "temperature"),
                _value_dimension("state", None, None) | {"name": "measurement state"},
            ],
        }
    ],
}

MULTITSFRAME_METADATA_EXAMPLE: dict[str, Any] = {
    "dataset_metadata": {
        "metric_key": "external_id",
        "queried_metrics": ["plant_a.pressure", "plant_a.temperature"],
        "ref_interval_start_timestamp": "2026-01-01T00:00:00+00:00",
        "ref_interval_end_timestamp": "2026-01-02T00:00:00+00:00",
        "ref_interval_type": "closed",
        "default_aggregation_interval": "1h",
        "default_timezone": "Europe/Berlin",
    },
    "metrics": [
        {
            "id": "c5a8e2f1-0b3d-4e6a-9f7c-1d2e3f4a5b6c",
            "external_id": "plant_a.pressure",
            "name": "Plant A pressure",
            "value_dimensions": [_value_dimension("value", "bar", "pressure")],
        },
        {
            "id": "8d7c6b5a-4f3e-4d2c-8b1a-0f9e8d7c6b5a",
            "external_id": "plant_a.temperature",
            "name": "Plant A temperature",
            "value_dimensions": [
                _value_dimension("value", "°C", "temperature") | {"deadband": 0.5, "decimals": 1}
            ],
            "default_aggregation_method": "MAX",
            "recording_mode": "on_change",
            "data_frequency": "1h",
        },
    ],
}

_SINGLE_METRIC_DESCRIPTION = (
    "Metadata of the single metric: exactly one metric, which has the field named by"
    " dataset_metadata.metric_key with the value of dataset_metadata.single_metric."
)


# the metric id field set when a metric gets another id, if the metric key field is taken
_METRIC_NAME_FIELD = "metric"


def _renamed[T: SharedValueDimensionMetadata](
    value_dimensions: tuple[T, ...] | None, column: str, new_column: str
) -> tuple[T, ...] | None:
    """Only the value dimensions of column, renamed to new_column, None if there are none"""
    renamed = tuple(
        value_dimension.model_copy(update={"column": new_column})
        for value_dimension in value_dimensions or ()
        if value_dimension.column == column
    )
    return renamed if len(renamed) > 0 else None


def _with_value_column(metric: MetricMetadata, column: str, new_column: str) -> MetricMetadata:
    """The metric with only the value dimension of column, renamed to new_column"""
    return metric.model_copy(
        update={"value_dimensions": _renamed(metric.value_dimensions, column, new_column) or ()}
    )


class SeriesMetadata(_TimeseriesMetadataBase):
    """hetida designer metadata conventions for a SERIES

    Structure of the metadata in the attrs attribute of a SERIES during execution, which is also
    exchanged with adapters, e.g. via the Data-Attributes header of the generic REST adapter
    timeseries endpoint (for each timeseries) or via the __metadata__ field of the wrapped format
    of the direct provisioning adapter.

    The fields that are not required are optional. Additional fields are allowed at every level.
    Timestamps are UTC isoformat strings with explicit offset (Z or +00:00).
    """

    model_config = ConfigDict(json_schema_extra={"examples": [SERIES_METADATA_EXAMPLE]})

    _data_type: ClassVar[TimeseriesDataType] = "SERIES"

    dataset_metadata: SingleMetricDatasetMetadata
    metrics: Annotated[tuple[MetricMetadata, ...], _item_count(1, 1)] = Field(
        ...,
        json_schema_extra={"minItems": 1, "maxItems": 1},
        description=_SINGLE_METRIC_DESCRIPTION,
    )

    def as_singletsframe(self, column: str = "value") -> "SingleTSFrameMetadata":
        """The metadata of the SINGLETSFRAME with the values of the SERIES in column

        Renames the value dimension "value" of the metric and the shared one to column.
        """
        return self._converted(
            SingleTSFrameMetadata,
            dataset_metadata=self.dataset_metadata,
            metrics=(_with_value_column(self.metric(), "value", column),),
            value_dimensions_shared=_renamed(self.value_dimensions_shared, "value", column),
        )


class SingleTSFrameMetadata(_TimeseriesMetadataBase):
    """hetida designer metadata conventions for a SINGLETSFRAME

    Structure of the metadata in the attrs attribute of a SINGLETSFRAME during execution, which
    is also exchanged with adapters, e.g. via the Data-Attributes header of the generic REST
    adapter singletsframe endpoint or via the __metadata__ field of the wrapped format of the
    direct provisioning adapter.

    The fields that are not required are optional. Additional fields are allowed at every level.
    Timestamps are UTC isoformat strings with explicit offset (Z or +00:00).
    """

    model_config = ConfigDict(json_schema_extra={"examples": [SINGLETSFRAME_METADATA_EXAMPLE]})

    _data_type: ClassVar[TimeseriesDataType] = "SINGLETSFRAME"

    dataset_metadata: SingleMetricDatasetMetadata
    metrics: Annotated[tuple[MetricMetadata, ...], _item_count(1, 1)] = Field(
        ...,
        json_schema_extra={"minItems": 1, "maxItems": 1},
        description=_SINGLE_METRIC_DESCRIPTION,
    )

    def as_series(self, column: str = "value") -> SeriesMetadata:
        """The metadata of the SERIES with the values of column

        Keeps only the value dimensions of column, renamed to "value". KeyError if the metric
        has no value dimension of column.
        """
        if column not in {vd.column for vd in self.metric().value_dimensions}:
            raise KeyError(column)
        return self._converted(
            SeriesMetadata,
            dataset_metadata=self.dataset_metadata,
            metrics=(_with_value_column(self.metric(), column, "value"),),
            value_dimensions_shared=_renamed(self.value_dimensions_shared, column, "value"),
        )

    def as_multitsframe(self, metric_id: str | None = None) -> "MultiTSFrameMetadata":
        """The metadata of the MULTITSFRAME of the single metric, named metric_id if given

        If metric_id differs from the id of the metric, it becomes its id: in the field named by
        the metric key if the metric does not have it, otherwise in the field "metric", which
        then becomes the metric key.
        """
        metric = self.metric()
        dataset_metadata = self.dataset_metadata.model_dump()
        if metric_id is not None and metric_id != self.metric_ids()[0]:
            metric_key = dataset_metadata["metric_key"]
            if lookup(metric, metric_key) is not None:
                metric_key = dataset_metadata["metric_key"] = _METRIC_NAME_FIELD
            metric = type(metric).model_validate(metric.model_dump() | {metric_key: metric_id})
        metric_id = lookup(metric, dataset_metadata["metric_key"])
        return self._converted(
            MultiTSFrameMetadata,
            dataset_metadata=dataset_metadata
            | {"single_metric": metric_id, "queried_metrics": [metric_id]},
            metrics=(metric,),
            value_dimensions_shared=self.value_dimensions_shared,
        )


class MultiTSFrameMetadata(_TimeseriesMetadataBase):
    """hetida designer metadata conventions for a MULTITSFRAME

    Structure of the metadata in the attrs attribute of a MULTITSFRAME during execution, which
    is also exchanged with adapters, e.g. via the Data-Attributes header of the generic REST
    adapter multitsframe endpoint or via the __metadata__ field of the wrapped format of the
    direct provisioning adapter.

    The fields that are not required are optional. Additional fields are allowed at every level.
    Timestamps are UTC isoformat strings with explicit offset (Z or +00:00).
    """

    model_config = ConfigDict(json_schema_extra={"examples": [MULTITSFRAME_METADATA_EXAMPLE]})

    _data_type: ClassVar[TimeseriesDataType] = "MULTITSFRAME"

    dataset_metadata: MultiTSFrameDatasetMetadata
    metrics: tuple[MetricMetadata, ...] = Field(
        ...,
        description="Metadata of the metrics: one for each metric in the data. Each metric must"
        " have the field named by dataset_metadata.metric_key as a string, unique among the"
        " metrics.",
    )

    def narrowed_to(self, metric_id: str) -> SingleTSFrameMetadata:
        """The metadata of the SINGLETSFRAME of one metric, KeyError if it has no metadata

        The metric is shared, not copied. It becomes the single and only queried metric.
        """
        return self._converted(
            SingleTSFrameMetadata,
            dataset_metadata=self.dataset_metadata.model_dump()
            | {"single_metric": metric_id, "queried_metrics": [metric_id]},
            metrics=(self.metric(metric_id),),
            value_dimensions_shared=self.value_dimensions_shared,
        )


METADATA_MODELS: dict[str, type[_TimeseriesMetadataBase]] = {
    "SERIES": SeriesMetadata,
    "SINGLETSFRAME": SingleTSFrameMetadata,
    "MULTITSFRAME": MultiTSFrameMetadata,
}


class MetadataIssueSeverity(StrEnum):
    """Severity of an issue found when checking metadata against the metadata conventions

    error: Violates the conventions, so helpers and components may misinterpret the metadata.
    warning: Likely a mistake, e.g. metadata not matching the data.
    """

    ERROR = "error"
    WARNING = "warning"


class MetadataConventionIssue(BaseModel):
    """Issue found when checking metadata against the metadata conventions"""

    severity: MetadataIssueSeverity
    location: str = Field(
        ...,
        description="Where the issue occurs, e.g. metrics[0].value_dimensions[1].column in the"
        " checked metadata. Empty for the checked object as a whole.",
    )
    message: str


class MetadataConventionError(ValueError):
    """Metadata violating the metadata conventions, with the issues found"""

    def __init__(self, issues: list[MetadataConventionIssue]) -> None:
        self.issues = issues
        super().__init__(
            "Violates the metadata conventions: "
            + _listing([f"{issue.location}: {issue.message}" for issue in issues], 5)
        )


def _error(location: str, message: str) -> MetadataConventionIssue:
    return MetadataConventionIssue(
        severity=MetadataIssueSeverity.ERROR, location=location, message=message
    )


def _warning(location: str, message: str) -> MetadataConventionIssue:
    return MetadataConventionIssue(
        severity=MetadataIssueSeverity.WARNING, location=location, message=message
    )


def _location(loc: tuple[int | str, ...]) -> str:
    """Format a pydantic error location like metrics[0].value_dimensions[1].column"""
    location = ""
    for part in loc:
        if isinstance(part, int):
            location += f"[{part}]"
        else:
            location += f".{part}" if location != "" else part
    return location


def _listing(items: list[str], max_items: int = 10) -> str:
    listed = ", ".join(f'"{item}"' for item in items[:max_items])
    if len(items) > max_items:
        listed += f" and {len(items) - max_items} more"
    return listed


def _check_duplicate_columns(
    value_dimensions: list[dict[str, Any]], location: str
) -> list[MetadataConventionIssue]:
    counts = Counter(value_dimension["column"] for value_dimension in value_dimensions)
    return [
        _error(location, f'Value dimension column "{column}" occurs more than once.')
        for column, count in counts.items()
        if count > 1
    ]


def _check_interval(
    obj: dict[str, Any], location: str, start_key: str, end_key: str
) -> list[MetadataConventionIssue]:
    """Check an interval given by start and end fields of the object at location"""
    start = obj.get(start_key)
    end = obj.get(end_key)
    if (start is None) != (end is None):
        missing_key = start_key if start is None else end_key
        return [
            _error(
                f"{location}.{missing_key}",
                f"Start and end of an interval must be provided together, but {missing_key}"
                " is missing.",
            )
        ]
    if start is not None and end is not None and pd.Timestamp(start) > pd.Timestamp(end):
        return [_error(f"{location}.{start_key}", f"Start is after end {end}.")]
    return []


@lru_cache(maxsize=1024)
def _is_frequency(value: str) -> bool:
    """Whether value is a Pandas date offset alias or a timedelta string

    A unit is required, since e.g. "1" would be a timedelta string of 1 nanosecond.
    """
    if re.search("[A-Za-z]", value) is None:
        return False
    try:
        pd.tseries.frequencies.to_offset(value)
    except ValueError:
        try:
            # e.g. "nan" gives NaT
            return bool(pd.notna(pd.to_timedelta(value)))
        except ValueError:
            return False
    return True


@lru_cache(maxsize=1024)
def _duration(value: str) -> pd.Timedelta | None:
    """The fixed duration of a frequency, None if calendar based like "MS" or no frequency"""
    try:
        offset = pd.tseries.frequencies.to_offset(value)
    except ValueError:
        try:
            # e.g. "P1D" or "1 days"
            duration = pd.to_timedelta(value)
        except ValueError:
            return None
        return None if pd.isna(duration) else duration
    if isinstance(offset, pd.offsets.Day):
        # a calendar day since pandas 3, i.e. 24 hours in UTC
        return pd.Timedelta(days=offset.n)
    if isinstance(offset, pd.offsets.Tick):
        return pd.Timedelta(offset)
    # calendar based, e.g. months
    return None


@lru_cache(maxsize=1024)
def _offset_count(value: str) -> int:
    """The count n of a calendar based frequency, e.g. 3 for "3MS\""""
    return int(pd.tseries.frequencies.to_offset(value).n)


def _not_a_frequency(location: str, value: str) -> MetadataConventionIssue:
    return _error(
        location,
        f'"{value}" is not a Pandas date offset alias or timedelta string, e.g. "15min".',
    )


def _check_frequency(
    obj: dict[str, Any], field: str, location: str
) -> list[MetadataConventionIssue]:
    """Check that a frequency field is a positive frequency"""
    value = obj.get(field)
    if value is None:
        return []
    if not _is_frequency(value):
        return [_not_a_frequency(f"{location}.{field}", value)]
    duration = _duration(value)
    positive = duration > pd.Timedelta(0) if duration is not None else _offset_count(value) > 0
    return [] if positive else [_error(f"{location}.{field}", f'"{value}" is not positive.')]


def _check_offset(
    obj: dict[str, Any], frequency_field: str, offset_field: str, location: str
) -> list[MetadataConventionIssue]:
    """Check the offset of the timestamps against the intervals of a valid frequency"""
    offset = obj[offset_field]
    offset_location = f"{location}.{offset_field}"
    if not _is_frequency(offset):
        return [_not_a_frequency(offset_location, offset)]
    offset_duration = _duration(offset)
    if offset_duration is None or offset_duration < pd.Timedelta(0):
        return [
            _error(offset_location, f'"{offset}" is not a non-negative timedelta, e.g. "4min".')
        ]
    # None for calendar based frequencies, which offsets cannot be compared with
    frequency_duration = _duration(obj[frequency_field])
    if frequency_duration is not None and offset_duration >= frequency_duration:
        return [
            _error(
                offset_location,
                f'"{offset}" is not smaller than {frequency_field} "{obj[frequency_field]}".',
            )
        ]
    return []


def _check_frequency_with_alignment(
    obj: dict[str, Any], frequency_field: str, offset_field: str, timezone_field: str, location: str
) -> list[MetadataConventionIssue]:
    """Check a frequency and the fields aligning its intervals, the offset and the time zone

    They are only meaningful together with the frequency on the same level, since the frequency
    of a metric falls back to the one of the dataset metadata as a whole.
    """
    issues = _check_frequency(obj, frequency_field, location)
    valid_frequency = len(issues) == 0 and obj.get(frequency_field) is not None
    for field in (offset_field, timezone_field):
        if obj.get(field) is not None and obj.get(frequency_field) is None:
            issues.append(_error(f"{location}.{field}", f"Requires {frequency_field}."))
    issues += _check_timezone(obj, location, timezone_field)
    if obj.get(offset_field) is not None and valid_frequency:
        issues += _check_offset(obj, frequency_field, offset_field, location)
    return issues


_UTC_OFFSET_PATTERN = re.compile(r"^[+-](0[0-9]|1[0-4]):[0-5][0-9]$")


@cache
def _timezone_names() -> frozenset[str]:
    """The IANA time zone names of the tzdata package, independent of the system

    Not zoneinfo.available_timezones, which also lists the files of the system's time zone
    database, e.g. "localtime" on Debian or Ubuntu, which is no time zone name.
    """
    with resources.files("tzdata").joinpath("zones").open(encoding="utf-8") as zones:
        return frozenset(line.strip() for line in zones if line.strip() != "")


def _is_timezone(value: str) -> bool:
    """Whether value is an IANA time zone name or a fixed UTC offset, e.g. "+02:00" """
    return _UTC_OFFSET_PATTERN.match(value) is not None or value in _timezone_names()


def _check_timezone(
    obj: dict[str, Any], location: str, field: str = "default_timezone"
) -> list[MetadataConventionIssue]:
    timezone = obj.get(field)
    if timezone is None or _is_timezone(timezone):
        return []
    return [
        _error(
            f"{location}.{field}",
            f'"{timezone}" is neither an IANA time zone name like "Europe/Berlin" nor a UTC'
            ' offset like "+02:00".',
        )
    ]


def _check_recording(
    metric: dict[str, Any], dataset_metadata: dict[str, Any], location: str
) -> list[MetadataConventionIssue]:
    """Check that the recording information of a metric fits its recording mode"""
    issues = []
    recording_mode = metric.get("recording_mode")
    if (
        metric.get("recording_aggregation_method") is not None
        and recording_mode != RecordingMode.PERIODIC
    ):
        issues.append(
            _error(
                f"{location}.recording_aggregation_method",
                "Only meaningful for recording_mode periodic.",
            )
        )
    if (
        recording_mode == RecordingMode.PERIODIC
        and metric.get("data_frequency") is None
        and dataset_metadata.get("ref_data_frequency") is None
    ):
        issues.append(
            _error(
                f"{location}.recording_mode",
                "periodic requires data_frequency or dataset_metadata.ref_data_frequency, the"
                " interval of the values.",
            )
        )
    if recording_mode != RecordingMode.ON_CHANGE:
        issues += [
            _warning(
                f"{location}.value_dimensions[{vd_index}].deadband",
                "Only meaningful if the recording_mode of the metric is on_change.",
            )
            for vd_index, value_dimension in enumerate(metric["value_dimensions"])
            if value_dimension.get("deadband") is not None
        ]
    return issues


def _known_fields(model: type[BaseModel]) -> set[str]:
    return set(model.model_fields)


# hints for fields placed where the conventions do not expect them
_MISPLACED_FIELD_HINTS: dict[tuple[type[BaseModel], str], str] = {
    (MetricMetadata, "unit"): 'Provide the unit of the value dimension "value" under'
    " value_dimensions instead.",
    (MetricMetadata, "measurement"): 'Provide the measurement of the value dimension "value"'
    " under value_dimensions instead.",
}


def _unknown_field_issues(
    obj: dict[str, Any], model: type[BaseModel], location: str, ignored: set[str] | None = None
) -> list[MetadataConventionIssue]:
    """Warnings for fields not defined by the conventions, which may be misspelled"""
    known = _known_fields(model)
    issues = []
    for field in obj:
        if field in known or (ignored is not None and field in ignored):
            continue
        hint = _MISPLACED_FIELD_HINTS.get((model, field))
        if hint is None:
            snake_case = re.sub(r"(?<!^)(?=[A-Z])", "_", field).lower()
            close_matches = (
                [snake_case]
                if snake_case in known
                else difflib.get_close_matches(field, known, n=1, cutoff=0.8)
            )
            hint = (
                f'Did you mean "{close_matches[0]}"?'
                if len(close_matches) > 0
                else "Additional fields are allowed, but make sure it is not misspelled."
            )
        issues.append(
            _warning(
                f"{location}.{field}" if location != "" else field,
                f'Unknown field "{field}". {hint}',
            )
        )
    return issues


def _dicts(value: Any) -> list[tuple[int, dict[str, Any]]]:
    """The dicts in value with their index, if value is a list"""
    if not isinstance(value, list):
        return []
    return [(index, item) for index, item in enumerate(value) if isinstance(item, dict)]


def _check_unknown_fields(
    attrs: Any, model: type[_TimeseriesMetadataBase]
) -> list[MetadataConventionIssue]:
    """Warnings for fields not defined by the conventions

    Also applied to structurally invalid metadata as far as possible, since a misspelled field
    often explains a missing required one.
    """
    if not isinstance(attrs, dict):
        return []
    issues = _unknown_field_issues(attrs, model, "")

    dataset_metadata = attrs.get("dataset_metadata")
    metric_key = None
    if isinstance(dataset_metadata, dict):
        metric_key = dataset_metadata.get("metric_key")
        dataset_metadata_model = model.model_fields["dataset_metadata"].annotation
        assert isinstance(dataset_metadata_model, type)  # for mypy  # noqa: S101
        issues += _unknown_field_issues(
            dataset_metadata, dataset_metadata_model, "dataset_metadata"
        )
        if isinstance(dataset_metadata.get("signal_group"), dict):
            issues += _unknown_field_issues(
                dataset_metadata["signal_group"],
                SignalGroupMetadata,
                "dataset_metadata.signal_group",
            )

    for index, value_dimension in _dicts(attrs.get("value_dimensions_shared")):
        issues += _unknown_field_issues(
            value_dimension, SharedValueDimensionMetadata, f"value_dimensions_shared[{index}]"
        )
    for index, metric in _dicts(attrs.get("metrics")):
        location = f"metrics[{index}]"
        # the field identifying the metric may be any field
        issues += _unknown_field_issues(metric, MetricMetadata, location, ignored={str(metric_key)})
        for vd_index, value_dimension in _dicts(metric.get("value_dimensions")):
            issues += _unknown_field_issues(
                value_dimension, ValueDimensionMetadata, f"{location}.value_dimensions[{vd_index}]"
            )
        for comment_index, comment in _dicts(metric.get("comments")):
            comment_location = f"{location}.comments[{comment_index}]"
            issues += _unknown_field_issues(comment, MetricComment, comment_location)
            for reply_index, reply in _dicts(comment.get("replies")):
                issues += _unknown_field_issues(
                    reply, MetricCommentReply, f"{comment_location}.replies[{reply_index}]"
                )
    return issues


_DEPRECATED_METRIC_FIELDS = {
    name: field.deprecated
    for name, field in MetricMetadata.model_fields.items()
    if field.deprecated is not None
}


def _check_consistency(attrs: dict[str, Any]) -> list[MetadataConventionIssue]:
    """Check the rules of the conventions which the JSON Schema cannot express

    Expects attrs to be valid against the JSON Schema of the data type.
    """
    issues: list[MetadataConventionIssue] = []
    dataset_metadata = attrs["dataset_metadata"]
    metrics = attrs["metrics"]
    metric_key = dataset_metadata["metric_key"]

    metric_ids = []
    for index, metric in enumerate(metrics):
        metric_id = metric.get(metric_key)
        if not isinstance(metric_id, str):
            issues.append(
                _error(
                    f"metrics[{index}]",
                    f'Metric has no string field "{metric_key}", which identifies metrics'
                    " according to dataset_metadata.metric_key.",
                )
            )
        else:
            metric_ids.append(metric_id)
        issues += [
            _warning(f"metrics[{index}].{name}", f"Deprecated. {deprecated}")
            for name, deprecated in _DEPRECATED_METRIC_FIELDS.items()
            if metric.get(name) is not None
        ]
        issues += _check_duplicate_columns(
            metric["value_dimensions"], f"metrics[{index}].value_dimensions"
        )
        issues += _check_frequency_with_alignment(
            metric,
            "data_frequency",
            "data_frequency_offset",
            "data_frequency_timezone",
            f"metrics[{index}]",
        )
        issues += _check_timezone(metric, f"metrics[{index}]")
        issues += _check_recording(metric, dataset_metadata, f"metrics[{index}]")
        for comment_index, comment in enumerate(metric.get("comments") or []):
            issues += _check_interval(
                comment, f"metrics[{index}].comments[{comment_index}]", "start_date", "end_date"
            )
    issues += [
        _error("metrics", f'Metric "{metric_id}" occurs more than once.')
        for metric_id, count in Counter(metric_ids).items()
        if count > 1
    ]
    issues += _check_duplicate_columns(
        attrs.get("value_dimensions_shared") or [], "value_dimensions_shared"
    )

    single_metric = dataset_metadata.get("single_metric")
    if single_metric is not None and len(metrics) > 1:
        issues.append(
            _error(
                "dataset_metadata.single_metric",
                f"Must not be set, since {len(metrics)} metrics are present under metrics.",
            )
        )
    elif single_metric is not None and len(metric_ids) == 1 and single_metric not in metric_ids:
        issues.append(
            _error(
                "dataset_metadata.single_metric",
                f'"{single_metric}" is not the "{metric_key}" of the metric under metrics.',
            )
        )
    elif single_metric is not None and single_metric not in dataset_metadata["queried_metrics"]:
        issues.append(_error("dataset_metadata.single_metric", "Missing in queried_metrics."))

    if dataset_metadata.get("only_invalidate") is True and (
        dataset_metadata.get("invalidate_dataset") is False
    ):
        issues.append(
            _error(
                "dataset_metadata.only_invalidate",
                "Cannot be true if invalidate_dataset is false.",
            )
        )

    if dataset_metadata.get("ref_dataset_discrete") is not True:
        issues += [
            _error(
                f"dataset_metadata.{field}",
                "Required unless dataset_metadata.ref_dataset_discrete is true.",
            )
            for field in REF_INTERVAL_FIELDS
            if dataset_metadata.get(field) is None
        ]
    issues += _check_interval(
        dataset_metadata,
        "dataset_metadata",
        "ref_interval_start_timestamp",
        "ref_interval_end_timestamp",
    )
    issues += _check_interval(
        dataset_metadata,
        "dataset_metadata",
        "invalidation_interval_start",
        "invalidation_interval_end",
    )
    issues += _check_frequency_with_alignment(
        dataset_metadata,
        "ref_data_frequency",
        "ref_data_frequency_offset",
        "ref_data_frequency_timezone",
        "dataset_metadata",
    )
    issues += _check_frequency(dataset_metadata, "default_aggregation_interval", "dataset_metadata")
    issues += _check_timezone(dataset_metadata, "dataset_metadata")
    return issues


_CLOSED_BY_INTERVAL_TYPE: dict[str, Literal["both", "neither", "left", "right"]] = {
    "closed": "both",
    "open": "neither",
    "left_closed": "left",
    "right_open": "left",
    "right_closed": "right",
    "left_open": "right",
}


def _check_data_in_ref_interval(
    dataset_metadata: dict[str, Any], data: pd.Series | pd.DataFrame
) -> list[MetadataConventionIssue]:
    """Warn if the data has timestamps outside of the ref interval"""
    start = dataset_metadata.get("ref_interval_start_timestamp")
    end = dataset_metadata.get("ref_interval_end_timestamp")
    interval_type = dataset_metadata.get("ref_interval_type")
    timestamps = data.index if isinstance(data, pd.Series) else data.get("timestamp")
    if (
        dataset_metadata.get("ref_dataset_discrete") is True
        or start is None
        or end is None
        or interval_type is None
        or pd.Timestamp(start) > pd.Timestamp(end)
        or timestamps is None
        or len(timestamps) == 0
        or not pd.api.types.is_datetime64_any_dtype(timestamps)
    ):
        return []
    ref_interval = pd.Interval(
        pd.Timestamp(start), pd.Timestamp(end), closed=_CLOSED_BY_INTERVAL_TYPE[interval_type]
    )
    # naive timestamps are considered to be UTC
    first, last = (
        timestamp if timestamp.tzinfo is not None else timestamp.tz_localize("UTC")
        for timestamp in (timestamps.min(), timestamps.max())
    )
    if first in ref_interval and last in ref_interval:
        return []
    return [
        _warning(
            "dataset_metadata",
            f"The data has timestamps outside of the {interval_type} ref interval: The first is"
            f" {first.isoformat()}, the last {last.isoformat()}.",
        )
    ]


def _check_metrics_of_data(
    attrs: dict[str, Any], data_type: TimeseriesDataType, data: pd.Series | pd.DataFrame | None
) -> list[MetadataConventionIssue]:
    """Check that the metrics of the data and the queried metrics are described"""
    issues: list[MetadataConventionIssue] = []
    dataset_metadata = attrs["dataset_metadata"]
    # metrics without a string id are reported by _check_consistency
    metric_ids = {
        metric_id
        for metric in attrs["metrics"]
        if isinstance(metric_id := metric.get(dataset_metadata["metric_key"]), str)
    }
    data_metrics: list[str] = []
    if data_type == "MULTITSFRAME" and isinstance(data, pd.DataFrame) and "metric" in data.columns:
        data_metrics = [str(metric) for metric in data["metric"].unique()]
        if len(missing := sorted(set(data_metrics) - metric_ids)) > 0:
            issues.append(
                _error(
                    "metrics",
                    f"Metrics of the metric column missing under metrics: {_listing(missing)}",
                )
            )
        queried_metrics = dataset_metadata["queried_metrics"]
        if len(unqueried := sorted(set(data_metrics) - set(queried_metrics))) > 0:
            issues.append(
                _error(
                    "dataset_metadata.queried_metrics",
                    f"Metrics of the metric column missing in queried_metrics:"
                    f" {_listing(unqueried)}",
                )
            )
    # queried metrics occurring in the data are reported as missing under metrics above
    undescribed_metrics = sorted(
        set(dataset_metadata["queried_metrics"]) - metric_ids - set(data_metrics)
    )
    if len(undescribed_metrics) > 0:
        issues.append(
            _warning(
                "metrics",
                f"Queried metrics without metadata under metrics: {_listing(undescribed_metrics)}",
            )
        )
    return issues


def _check_consistency_with_data_type(
    attrs: dict[str, Any], data_type: TimeseriesDataType, data: pd.Series | pd.DataFrame | None
) -> list[MetadataConventionIssue]:
    """Check the rules specific to the data type and whether the metadata matches the data"""
    metrics = attrs["metrics"]
    issues = _check_metrics_of_data(attrs, data_type, data)
    if data is not None:
        issues += _check_data_in_ref_interval(attrs["dataset_metadata"], data)

    # the value columns of frames are only known from their data
    value_columns: set[str] | None = None
    if data_type == "SERIES":
        value_columns = {"value"}
    elif isinstance(data, pd.DataFrame):
        value_columns = set(data.columns) - (
            {"timestamp", "metric"} if data_type == "MULTITSFRAME" else {"timestamp"}
        )
    if value_columns is None:
        return issues

    for index, metric in enumerate(metrics):
        described_columns = {
            value_dimension["column"] for value_dimension in metric["value_dimensions"]
        }
        if len(undescribed := sorted(value_columns - described_columns)) > 0:
            issues.append(
                _error(
                    f"metrics[{index}].value_dimensions",
                    f"Value columns of the {data_type} without value dimension:"
                    f" {_listing(undescribed)}",
                )
            )

    value_dimension_lists = [
        (f"metrics[{index}].value_dimensions", metric["value_dimensions"])
        for index, metric in enumerate(metrics)
    ] + [("value_dimensions_shared", attrs.get("value_dimensions_shared") or [])]
    for location, value_dimensions in value_dimension_lists:
        for index, value_dimension in enumerate(value_dimensions):
            if value_dimension["column"] not in value_columns:
                issues.append(
                    _warning(
                        f"{location}[{index}].column",
                        f'Column "{value_dimension["column"]}" is not a value column of the'
                        f" {data_type}.",
                    )
                )
    return issues


_SKIP_RULES = "skip_rules_of_metadata_conventions"


def _rule_errors(
    data: Any, model: _TimeseriesMetadataBase, data_type: TimeseriesDataType
) -> list[MetadataConventionIssue]:
    """The errors of the rules which JSON Schema cannot express, for valid structure

    The rules are checked on the input if it is in JSON form, otherwise on the model's dump, e.g.
    for input with nested models.
    """

    def errors(attrs: dict[str, Any]) -> list[MetadataConventionIssue]:
        issues = _check_consistency(attrs) + _check_consistency_with_data_type(
            attrs, data_type, None
        )
        return [issue for issue in issues if issue.severity == MetadataIssueSeverity.ERROR]

    if isinstance(data, dict):
        try:
            return errors(data)
        except (AttributeError, KeyError, TypeError):
            pass
    return errors(model.model_dump(mode="json"))


def _metric_rule_errors(
    meta: _TimeseriesMetadataBase, metric: MetricMetadata
) -> list[MetadataConventionIssue]:
    """The rule errors concerning a single metric, together with the dataset metadata"""
    attrs = {
        "dataset_metadata": meta.dataset_metadata.model_dump(mode="json"),
        "metrics": [metric.model_dump(mode="json")],
    }
    if meta.value_dimensions_shared is not None:
        attrs["value_dimensions_shared"] = [
            value_dimension.model_dump(mode="json")
            for value_dimension in meta.value_dimensions_shared
        ]
    issues = _check_consistency(attrs) + _check_consistency_with_data_type(
        attrs, meta._data_type, None
    )
    return [issue for issue in issues if issue.severity == MetadataIssueSeverity.ERROR]


def check_metadata_conventions(
    obj: pd.Series | pd.DataFrame | Mapping[str, Any],
    data_type: TimeseriesDataType | None = None,
) -> list[MetadataConventionIssue]:
    """Check metadata against the metadata conventions of its data type

    obj is either a SERIES, SINGLETSFRAME or MULTITSFRAME, whose attrs are then also checked for
    consistency with its data, or the metadata itself. For metadata, data_type is required. For
    data it is inferred if not provided: A DataFrame with a "metric" column is considered to be a
    MULTITSFRAME, otherwise a SINGLETSFRAME.

    The metadata is checked in its JSON representation, as it is exchanged with adapters.
    Consistency is only checked if the structure is valid.

    Returns the found issues, i.e. an empty list if the metadata adheres to the conventions.
    """
    # imported here, since hdhelpers.metadata.attached imports this module
    from hdhelpers.metadata.attached import attrs_to_json  # noqa: PLC0415

    data = obj if isinstance(obj, pd.Series | pd.DataFrame) else None
    attrs = data.attrs if data is not None else obj
    if isinstance(attrs, Mapping):
        # attached metadata in its JSON form
        attrs = attrs_to_json(attrs)
    if data_type is None and isinstance(data, pd.Series):
        data_type = "SERIES"
    elif data_type is None and isinstance(data, pd.DataFrame):
        data_type = "MULTITSFRAME" if "metric" in data.columns else "SINGLETSFRAME"
    elif data_type is None:
        raise ValueError("The data type is required for checking metadata without data.")
    model = METADATA_MODELS[data_type]

    try:
        attrs_json = json.dumps(attrs, allow_nan=False)
    except (TypeError, ValueError) as e:
        return [
            _error(
                "",
                f"Metadata is not JSON serializable, so it cannot be exchanged with adapters: {e}",
            )
        ]

    try:
        model.model_validate_json(attrs_json, context={_SKIP_RULES: True})
    except ValidationError as e:
        issues = []
        for error in e.errors():
            message = error["msg"].removeprefix("Value error, ")
            if (error.get("ctx") or {}).get("pattern") == UTC_TIMESTAMP_PATTERN:
                message = (
                    "Should be a UTC isoformat timestamp with explicit offset, i.e. ending with Z"
                    f" or +00:00, got {error['input']!r}."
                )
            elif (
                error["loc"] == ("metrics",)
                and isinstance(attrs, Mapping)
                and isinstance(attrs.get("metrics"), dict)
            ):
                message += (
                    ". Metrics as a mapping is an older metadata convention, the current one"
                    " expects a list of metric objects."
                )
            issues.append(_error(_location(error["loc"]), message))
        return issues + _check_unknown_fields(json.loads(attrs_json), model)

    json_attrs = json.loads(attrs_json)
    return (
        _check_consistency(json_attrs)
        + _check_consistency_with_data_type(json_attrs, data_type, data)
        + _check_unknown_fields(json_attrs, model)
    )
