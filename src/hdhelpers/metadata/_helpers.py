from collections import defaultdict
from collections.abc import Callable, Collection
from typing import Any, cast

import pandas as pd
from glom import Check, Coalesce, CoalesceError, Spec, glom

import hdhelpers.metadata._current_convention as _current_convention
import hdhelpers.metadata._specs as _specs


def check_dataframe(data: pd.DataFrame):
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Input is not a pd.DataFrame")


def check_series(series: pd.Series):
    if not isinstance(series, pd.Series):
        raise TypeError("Input is not a pd.Series.")


def check_series_or_dataframe(data: pd.Series | pd.DataFrame):
    if not isinstance(data, pd.Series) and not isinstance(data, pd.DataFrame):
        raise TypeError("Input is not a pd.Series or pd.DataFrame.")


def spec_not_none(spec: str | Spec) -> Spec:
    """this entries must be given in the spec"""
    # TODO: Given the suite of tools introduced with Match, the Check specifier type may be deprecated in a future release
    return (spec, Check(validate=lambda x: x is not None))


def extract_from_metadata(metadata: Any, key: str, default: str | None = None) -> Any:
    return glom(metadata, Coalesce(f"dataset_metadata.{key}", default=default))


def _legacy_value_dimension_info(
    attrs: Any, value_dim_info: str | Spec
) -> defaultdict[str, defaultdict[str, Any]]:
    """get_value_dimension_info for older metadata structures"""
    return defaultdict(
        lambda: defaultdict(lambda: None),
        glom(attrs, _specs.by_metric_key_by_val_dimension(value_dim_info)),
    )


def get_value_dimension_info(
    multitsframe: pd.DataFrame | pd.Series,
    value_dim_info: str | Spec,
    include_inherited: bool = False,
) -> defaultdict[str, defaultdict[str, Any]]:
    """Obtain metadata info associated to the value dimensions of the metrics

    Returns a default dict whose values are the entries of the metrics metadata specified via
    "metric_key" in "dataset_metadata".

    Its values are defaultdicts whose keys are the "column" entries of the value dimension
    objects of that metric and whose values are extracted from the value_dimension object
    using using value_dim_info as a glom Spec, typically just a subfield.

    For the default "value" value dimension, if no concrete / explicit information is available
    for this value dimension, a corresponding entry in the metric object may be used.

    For all value dimensions, if no concrete explicit information is available for that value
    dimension in the value_dimensions list under the metric, the global "value_dimensions_shared"
    field of the attrs object is searched for corresponding information.

    If include_inherited, the properties a metric inherits are used as last resort for the
    "value" value dimension, i.e. after "value_dimensions_shared".

    If no information is found, None is set as value and is the default value of the
    inner default dict.

    For metadata following the current metadata convention, value_dim_info is only applied to
    the levels needed and entries not adhering to the conventions are skipped, see
    _current_convention.

    For examples we refer to the corresponding unit tests (/tests/helpers/test_metadata.py).
    """
    gathered = _current_convention.gather(multitsframe.attrs)
    if gathered is not None:
        return _current_convention.value_dimension_info(
            gathered, [value_dim_info], include_inherited
        )
    return _legacy_value_dimension_info(multitsframe.attrs, value_dim_info)


def value_dimension_info_with_fallbacks(
    data: pd.DataFrame | pd.Series,
    fields: tuple[str | Spec, ...],
    legacy_spec: Spec,
    include_inherited: bool = False,
) -> defaultdict[str, defaultdict[str, Any]]:
    """Obtain a field of the value dimensions, falling back to further fields

    For metadata following the current metadata convention, each field is looked up on all
    levels described in get_value_dimension_info (the value dimension, the metric for the
    value dimension "value" and "value_dimensions_shared") before the next field is tried.
    So e.g. a display name of the metric wins over the name of its value dimension. Fields
    provided as null are treated as missing. Inherited properties are only used if none of the
    fields is provided by the metadata itself.

    Older metadata structures are handled via legacy_spec, keeping their established behaviour.
    """
    gathered = _current_convention.gather(data.attrs)
    if gathered is None:
        return _legacy_value_dimension_info(data.attrs, legacy_spec)
    return _current_convention.value_dimension_info(gathered, fields, include_inherited)


_SINGLE_METRIC_KEY = "single_metric"


def _single_metric_name(attrs: Any) -> str | None:
    """The metric named by _SINGLE_METRIC_KEY in "dataset_metadata", if it is a string"""
    metric = extract_from_metadata(attrs, key=_SINGLE_METRIC_KEY)
    return metric if isinstance(metric, str) else None


def _single_metric(attrs: Any, metrics: Collection[str]) -> str | None:
    """The single metric of a SingleTSFrame or Series among the metrics present

    The single metric is identified via _SINGLE_METRIC_KEY in "dataset_metadata", values which
    are no strings count as missing. If it is missing but exactly one metric is present, that
    one is used, since a SingleTSFrame or Series cannot be ambiguous in this respect. Otherwise
    None is returned - also if the identified metric is not present, since the only metric
    present is another one then.
    """
    metric = _single_metric_name(attrs)
    if metric is not None:
        return metric if metric in metrics else None

    if len(metrics) == 1:
        return next(iter(metrics))

    return None


def _select_single_metric(info_by_metric: dict, attrs: Any, empty: Any) -> Any:
    """Pick the entry of the single metric (see _single_metric) out of a by-metric mapping

    `empty` is returned if the single metric cannot be determined.
    """
    metric = _single_metric(attrs, info_by_metric)
    return empty if metric is None else info_by_metric[metric]


def _single_metric_info(
    attrs: Any,
    current: Callable[[_current_convention.GatheredMetadata], dict[str, Any]],
    legacy: Callable[[], dict[str, Any]],
    empty: Any,
) -> Any:
    """Information of the single metric of a SingleTSFrame or Series (see _single_metric)

    For metadata following the current metadata convention, `current` gets the gathered metadata
    of the single metric only, so that no information of the other metrics is resolved - of
    which there may be many, e.g. for a Series taken from a MultiTSFrame. For older metadata
    structures, the entry of the single metric is picked out of the result of `legacy`.

    `empty` is returned if the single metric cannot be determined.
    """
    gathered = _current_convention.gather(attrs)
    if gathered is None:
        return _select_single_metric(legacy(), attrs, empty)

    metric = _single_metric(attrs, gathered.metrics)
    if metric is None:
        return empty
    return current(_current_convention.restricted_to(gathered, metric))[metric]


def singlets_value_dimension_info(
    singletsframe: pd.DataFrame, value_dim_info: str | Spec, include_inherited: bool = False
) -> defaultdict[str, Any]:
    """Metadata info of the value dimensions of the single metric of a SingleTSFrame

    A SingleTSFrame holds exactly one metric but - like a MultiTSFrame - arbitrarily many
    value dimensions. So in contrast to get_value_dimension_info (which is keyed by metric
    first) this returns a defaultdict keyed by value dimension column name only.

    The single metric is identified via "dataset_metadata.single_metric". If that is missing
    but the metadata contains exactly one metric, that metric is used, since a SingleTSFrame
    cannot be ambiguous in this respect.

    What is extracted per value dimension is exactly what get_value_dimension_info extracts -
    only the metric level is collapsed away.
    """
    return singlets_value_dimension_info_with_fallbacks(
        singletsframe, (value_dim_info,), value_dim_info, include_inherited
    )


def singlets_value_dimension_info_with_fallbacks(
    singletsframe: pd.DataFrame,
    fields: tuple[str | Spec, ...],
    legacy_spec: Spec,
    include_inherited: bool = False,
) -> defaultdict[str, Any]:
    """Counterpart of value_dimension_info_with_fallbacks for SingleTSFrames

    Like singlets_value_dimension_info, the result is keyed by value dimension only.
    """
    return _single_metric_info(
        singletsframe.attrs,
        lambda gathered: _current_convention.value_dimension_info(
            gathered, fields, include_inherited
        ),
        lambda: _legacy_value_dimension_info(singletsframe.attrs, legacy_spec),
        empty=defaultdict(lambda: None),
    )


# the metric of a Series in older metadata structures, used if "single_metric" is missing
_LEGACY_SERIES_METRIC = "series"


def series_value_info(
    series: pd.Series, fields: tuple[str | Spec, ...], legacy_spec: Spec, include_inherited: bool
) -> Any:
    """Info of the value dimension "value" of the single metric of a Series

    Each field is looked up as described in value_dimension_info_with_fallbacks. The single
    metric is determined like for SingleTSFrames, see singlets_value_dimension_info. Only older
    metadata structures name the metric of a Series "series", which is used if "single_metric"
    is missing.
    """

    def legacy() -> dict[str, Any]:
        info_by_metric = _legacy_value_dimension_info(series.attrs, legacy_spec)
        if _single_metric_name(series.attrs) is None and _LEGACY_SERIES_METRIC in info_by_metric:
            return {_LEGACY_SERIES_METRIC: info_by_metric[_LEGACY_SERIES_METRIC]}
        return info_by_metric

    return _single_metric_info(
        series.attrs,
        lambda gathered: _current_convention.value_dimension_info(
            gathered, fields, include_inherited
        ),
        legacy,
        empty={},
    ).get("value")


def _legacy_metric_info(attrs: Any, metric_info: str | Spec) -> dict[str, Any]:
    """metric_info_by_metric for older metadata structures"""
    try:
        return glom(attrs, _specs.spec_by_metric_key(metric_info))  # type: ignore[no-any-return]
    except CoalesceError:  # no metric metadata present at all
        return {}


def metric_info_by_metric(
    data: pd.DataFrame | pd.Series, metric_info: str | Spec, include_inherited: bool = True
) -> dict[str, Any]:
    """Obtain metadata info associated to the metrics, keyed by metric

    For metadata following the current metadata convention, information the metric itself does
    not provide is taken from its value dimension "value", then from "value_dimensions_shared"
    and, if include_inherited, finally from the properties the metric inherits. Information
    provided as null counts as missing. metric_info is only applied to the levels needed and
    entries not adhering to the conventions are skipped, see _current_convention.

    Returns an empty dict if no metric metadata is present at all. Errors raised by applying
    metric_info, e.g. a transformation failing on null, are not caught.
    """
    gathered = _current_convention.gather(data.attrs)
    if gathered is not None:
        return _current_convention.metric_info(gathered, metric_info, include_inherited)
    return _legacy_metric_info(data.attrs, metric_info)


def singlets_metric_info(
    singletsframe: pd.DataFrame, metric_info: str | Spec, include_inherited: bool = True
) -> Any:
    """Metadata of the single metric of a SingleTSFrame

    Counterpart of get_metric_info for SingleTSFrames: instead of a mapping keyed by metric
    this directly returns the requested information for the one metric, or None if it cannot
    be determined - which includes the case of absent metric metadata, since components should
    not require metadata (see the metadata conventions documentation).
    """
    return _single_metric_info(
        singletsframe.attrs,
        lambda gathered: _current_convention.metric_info(gathered, metric_info, include_inherited),
        lambda: _legacy_metric_info(singletsframe.attrs, metric_info),
        empty=None,
    )


def _string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) and value != "" else None


def _dataset_default_timezone(attrs: Any) -> str | None:
    return _string_or_none(extract_from_metadata(attrs, key=_specs.DEFAULT_TIMEZONE))


def _default_timezones(
    gathered: _current_convention.GatheredMetadata | None, dataset_timezone: str | None
) -> defaultdict[str, str | None]:
    own_timezones = (
        {}
        if gathered is None
        else _current_convention.own_metric_info(gathered, _specs.DEFAULT_TIMEZONE)
    )
    return defaultdict(
        lambda: dataset_timezone,
        {
            metric: _string_or_none(timezone) or dataset_timezone
            for metric, timezone in own_timezones.items()
        },
    )


def default_timezone_by_metric(data: pd.DataFrame | pd.Series) -> defaultdict[str, str | None]:
    """The default time zone of each metric, falling back to the one of the dataset metadata

    As specified by the metadata conventions, the default time zone of a metric only falls back
    to the one of the dataset metadata, not to its value dimensions or inherited properties.
    The default of the returned defaultdict is the one of the dataset metadata, since it applies
    to all metrics without their own. Values which are no (non-empty) strings count as missing.
    """
    return _default_timezones(
        _current_convention.gather(data.attrs), _dataset_default_timezone(data.attrs)
    )


def single_metric_default_timezone(data: pd.DataFrame | pd.Series) -> str | None:
    """The default time zone of the single metric of a Series or SingleTSFrame

    Falls back to the one of the dataset metadata, also if the single metric is not found.
    """
    dataset_timezone = _dataset_default_timezone(data.attrs)
    return cast(
        str | None,
        _single_metric_info(
            data.attrs,
            lambda gathered: _default_timezones(gathered, dataset_timezone),
            dict,  # older metadata structures provide no default time zones of the metrics
            empty=dataset_timezone,
        ),
    )
