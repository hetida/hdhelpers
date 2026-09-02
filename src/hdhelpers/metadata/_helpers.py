from collections import defaultdict
from typing import Any

import pandas as pd
from glom import Check, Coalesce, GlomError, Spec, glom

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
    multitsframe: pd.DataFrame | pd.Series, value_dim_info: str | Spec
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

    If no information is found, None is set as value and is the default value of the
    inner default dict.

    For examples we refer to the corresponding unit tests (/tests/helpers/test_metadata.py).
    """
    spec = _specs.by_metric_key_by_val_dimension(value_dim_info)
    value_dimension_info_by_metric_by_value_dimension = glom(multitsframe.attrs, spec)
    return defaultdict(
        lambda: defaultdict(lambda: None), value_dimension_info_by_metric_by_value_dimension
    )


_SINGLE_METRIC_KEY = "single_metric"


def _select_single_metric(info_by_metric: dict, attrs: Any, empty: Any) -> Any:
    """Pick the entry of the one metric of a SingleTSFrame out of a by-metric mapping

    The single metric is identified via _SINGLE_METRIC_KEY in "dataset_metadata". If that is
    missing but exactly one metric is present, that one is used, since a SingleTSFrame cannot
    be ambiguous in this respect. Otherwise `empty` is returned.
    """
    metric = extract_from_metadata(attrs, key=_SINGLE_METRIC_KEY)
    if metric is not None and metric in info_by_metric:
        return info_by_metric[metric]

    if len(info_by_metric) == 1:
        return next(iter(info_by_metric.values()))

    return empty


def singlets_value_dimension_info(
    singletsframe: pd.DataFrame, value_dim_info: str | Spec
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
        get_value_dimension_info(singletsframe, value_dim_info),
        singletsframe.attrs,
        empty=defaultdict(lambda: None),
    )


def singlets_metric_info(singletsframe: pd.DataFrame, metric_info: str | Spec) -> Any:
    """Metadata of the single metric of a SingleTSFrame

    Counterpart of get_metric_info for SingleTSFrames: instead of a mapping keyed by metric
    this directly returns the requested information for the one metric, or None if it cannot
    be determined - which includes the case of absent metric metadata, since components should
    not require metadata (see the metadata conventions documentation).
    """
    try:
        info_by_metric = glom(singletsframe.attrs, _specs.spec_by_metric_key(metric_info))
    except GlomError:  # no metric metadata present at all
        return None

    return _select_single_metric(info_by_metric, singletsframe.attrs, empty=None)
