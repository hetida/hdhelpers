from collections import defaultdict
from typing import Any

import pandas as pd
from glom import Check, Coalesce, CoalesceError, Spec, glom

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

    For examples we refer to the corresponding unit tests (/tests/helpers/test_metadata.py).
    """
    return defaultdict(
        lambda: defaultdict(lambda: None),
        _value_dimension_info_of_attrs(multitsframe.attrs, value_dim_info, include_inherited),
    )


def _value_dimension_info_of_attrs(
    attrs: Any, value_dim_info: str | Spec, include_inherited: bool = False
) -> Any:
    spec = _specs.by_metric_key_by_val_dimension(value_dim_info, include_inherited)
    return glom(attrs, spec)


def follows_current_convention(attrs: Any) -> bool:
    """Whether metadata follows the current metadata convention, i.e. has a list of metrics"""
    return isinstance(attrs, dict) and isinstance(attrs.get("metrics"), list)


def _restricted_to_metrics(attrs: dict, metrics: set) -> dict:
    """The metadata with only the metric objects of the given metrics

    The information of a metric is extracted independently of the other metrics, so fallbacks
    only need to be evaluated for the metrics still lacking information. Besides saving time
    for frames with many metrics, this avoids applying a spec to fallback levels whose values
    (e.g. null) the spec cannot handle, while the metric itself provides the information.

    Only for metadata following the current metadata convention.
    """
    metric_key = extract_from_metadata(attrs, key="metric_key", default="id")
    return attrs | {
        "metrics": [
            metric
            for metric in attrs["metrics"]
            if isinstance(metric, dict) and metric.get(metric_key) in metrics
        ]
    }


def _metrics_lacking_info(info_by_metric_by_value_dimension: dict) -> set:
    return {
        metric
        for metric, info_by_value_dimension in info_by_metric_by_value_dimension.items()
        if any(info is None for info in info_by_value_dimension.values())
    }


def value_dimension_info_with_fallbacks(
    data: pd.DataFrame | pd.Series,
    fields: tuple[str, ...],
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
    if not follows_current_convention(data.attrs):
        return get_value_dimension_info(data, legacy_spec, include_inherited)

    result: defaultdict[str, defaultdict[str, Any]] = defaultdict(lambda: defaultdict(lambda: None))
    attrs = data.attrs
    for field in fields:
        info_by_metric = _value_dimension_info_of_attrs(attrs, Coalesce(field, default=None))
        for metric, info_by_value_dimension in info_by_metric.items():
            for value_dimension, info in info_by_value_dimension.items():
                if result[metric][value_dimension] is None:
                    result[metric][value_dimension] = info

        # further fields only for the metrics still lacking information
        metrics_lacking_info = _metrics_lacking_info(result)
        if len(metrics_lacking_info) == 0:
            return result
        attrs = _restricted_to_metrics(data.attrs, metrics_lacking_info)

    if include_inherited:
        # inherited properties only after all fields of the metadata itself and, as in
        # get_value_dimension_info, only for the value dimension "value"
        for field in fields:
            metrics_lacking_value_info = {
                metric
                for metric, info_by_value_dimension in result.items()
                if info_by_value_dimension["value"] is None
            }
            if len(metrics_lacking_value_info) == 0:
                break
            inherited_by_metric = glom(
                _restricted_to_metrics(data.attrs, metrics_lacking_value_info),
                _specs.inherited_by_metric_key(Coalesce(field, default=None)),
            )
            for metric in metrics_lacking_value_info:
                result[metric]["value"] = inherited_by_metric.get(metric)
    return result


_SINGLE_METRIC_KEY = "single_metric"


def _select_single_metric(info_by_metric: dict, attrs: Any, empty: Any) -> Any:
    """Pick the entry of the one metric of a SingleTSFrame or Series out of a by-metric mapping

    The single metric is identified via _SINGLE_METRIC_KEY in "dataset_metadata". If that is
    missing but exactly one metric is present, that one is used, since a SingleTSFrame or
    Series cannot be ambiguous in this respect. Otherwise `empty` is returned.
    """
    metric = extract_from_metadata(attrs, key=_SINGLE_METRIC_KEY)
    if metric is not None and metric in info_by_metric:
        return info_by_metric[metric]

    if len(info_by_metric) == 1:
        return next(iter(info_by_metric.values()))

    return empty


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
    return _select_single_metric(
        get_value_dimension_info(singletsframe, value_dim_info, include_inherited),
        singletsframe.attrs,
        empty=defaultdict(lambda: None),
    )


def singlets_value_dimension_info_with_fallbacks(
    singletsframe: pd.DataFrame,
    fields: tuple[str, ...],
    legacy_spec: Spec,
    include_inherited: bool = False,
) -> defaultdict[str, Any]:
    """Counterpart of value_dimension_info_with_fallbacks for SingleTSFrames

    Like singlets_value_dimension_info, the result is keyed by value dimension only.
    """
    return _select_single_metric(
        value_dimension_info_with_fallbacks(singletsframe, fields, legacy_spec, include_inherited),
        singletsframe.attrs,
        empty=defaultdict(lambda: None),
    )


def metric_info_by_metric(
    data: pd.DataFrame | pd.Series, metric_info: str | Spec, include_inherited: bool = True
) -> dict[str, Any]:
    """Obtain metadata info associated to the metrics, keyed by metric

    For metadata following the current metadata convention, information the metric itself does
    not provide is taken from its value dimension "value", then from "value_dimensions_shared"
    and, if include_inherited, finally from the properties the metric inherits. Information
    provided as null counts as missing. The fallbacks are only evaluated for metrics lacking the
    information, see _restricted_to_metrics.

    Returns an empty dict if no metric metadata is present at all. Errors raised by applying
    metric_info, e.g. a transformation failing on null, are not caught.
    """
    try:
        info_by_metric = glom(data.attrs, _specs.spec_by_metric_key(metric_info))
    except CoalesceError:  # no metric metadata present at all
        return {}

    if not follows_current_convention(data.attrs):
        return info_by_metric

    metrics_lacking_info = {metric for metric, info in info_by_metric.items() if info is None}
    if len(metrics_lacking_info) == 0:
        return info_by_metric

    value_dimension_info = _value_dimension_info_of_attrs(
        _restricted_to_metrics(data.attrs, metrics_lacking_info),
        Coalesce(metric_info, default=None),
        include_inherited,
    )
    return {
        metric: info if info is not None else value_dimension_info.get(metric, {}).get("value")
        for metric, info in info_by_metric.items()
    }


def singlets_metric_info(
    singletsframe: pd.DataFrame, metric_info: str | Spec, include_inherited: bool = True
) -> Any:
    """Metadata of the single metric of a SingleTSFrame

    Counterpart of get_metric_info for SingleTSFrames: instead of a mapping keyed by metric
    this directly returns the requested information for the one metric, or None if it cannot
    be determined - which includes the case of absent metric metadata, since components should
    not require metadata (see the metadata conventions documentation).
    """
    return _select_single_metric(
        metric_info_by_metric(singletsframe, metric_info, include_inherited),
        singletsframe.attrs,
        empty=None,
    )
