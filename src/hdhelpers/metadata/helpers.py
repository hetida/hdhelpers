"""Helper functions for metadata extraction

This module provides functions to help extracting information from metadata
provided as .attrs with pandas DataFrame / Series objects following the hetida
designer metadata conventions.

They properly cascade defaults / fallbacks
and try to provide backwards compatible access to metadata for different versions
of the metadata conventions or simpler metadata structures.
"""

import datetime
from collections import defaultdict
from typing import Any, cast

import pandas as pd
from glom import Coalesce, Spec, glom

from hdhelpers.metadata.private import (
    get_value_dimension_info,
    spec_not_none,
)
from hdhelpers.metadata.specs import spec_by_metric_key


def get_units(
    multitsframe: pd.DataFrame,
) -> defaultdict[str, defaultdict[str, str | None]]:
    """Gets unit of value dimensions in MTS metrics from Metadata

    Args:
        multitsframe (pd.DataFrame): MTS with metadata following the convention.

    Returns:
        dict[str, dict[str | None] | None]: Dictionary of metrics containing the names of the value dimensions.
        If the short display name of the value_dimension is not present it returns the result of get_value_dimension_info().

    Raises:
        TypeError: If `multitsframe` is not a DataFrame.

    .. doctest::

        >>> from hdhelpers.metadata import get_units
        >>> attr = {
        ...    "by_metric": {
        ...        "metric1": {
        ...           "value_dimension": {
        ...                "value_dim_1": {
        ...                    "unit": "m"
        ...                }
        ...            }
        ...        },
        ...        "metric2": {
        ...                "value_dim_1": {
        ...                    "name": "name_of_value_dim_1"
        ...                }
        ...        },
        ...        "metric3": {
        ...            "value_dim_1": {},
        ...            "value_dim_2": {
        ...                "unit": "km"
        ...            }
        ...        }
        ...    }
        ... }
        >>> dataframe = pd.DataFrame()
        >>> dataframe.attrs = attr
        >>> get_units(dataframe)
        { "metric1": {"value_dim_1": "m"}, "metric2": {"value_dim_1": None}, "metric3:  {"value_dim_1": None, "value_dim_2": "km"}}
    """
    return get_value_dimension_info(multitsframe, "unit")


def get_names(multitsframe: pd.DataFrame) -> defaultdict[str, defaultdict[str, str | None]]:
    return get_value_dimension_info(multitsframe, Coalesce("name", default=None))


def get_display_names(multitsframe: pd.DataFrame) -> defaultdict[str, defaultdict[str, str | None]]:
    return get_value_dimension_info(multitsframe, Coalesce("display_name", "name", default=None))


def get_short_display_names(
    multitsframe: pd.DataFrame,
) -> defaultdict[str, defaultdict[str, str | None]]:
    return get_value_dimension_info(
        multitsframe, Coalesce("short_display_name", "display_name", "name", default=None)
    )


def get_measurements(multitsframe: pd.DataFrame) -> defaultdict[str, defaultdict[str, str | None]]:
    return get_value_dimension_info(multitsframe, "measurement")


def get_metric_info(multitsframe: pd.DataFrame, metric_info: str | Spec) -> defaultdict[str, Any]:
    """Obtain a defaultdict of metadata associated to metrics

    In contrast to metadata associated to concrete value dimensions, this
    function abstracts access to metadata associated to the underlying metric.

    The keys are the entries of the metrics metadata specified via
    "metric_key" in "dataset_metadata".

    The values are the entries specified via metric_info in the metrics metadata.
    Note that metric_info is interpreted as a glom Spec.

    The default value of the default dict is None.

    .. doctest::

        >>> from hdhelpers.metadata import get_series_unit
        >>> multitsframe.attrs = {
        ...    "dataset_metadata": {
        ...        "metric_key": "id"
        ...    },
        ...    "metrics": [
        ...        {
        ...            "id": "first",
        ...            "external_id": "external_first",
        ...            "unit": "m",
        ...            "display_name": "first display name",
        ...            "value_dimensions": [
        ...                {
        ...                    "column": "temp",
        ...                    "unit": "C",
        ...                    "measurement": "temperature"
        ...                }
        ...            ]
        ...        },
        ...        {
        ...            "id": "second",
        ...            "name": "second name",
        ...            "external_id": "external_second",
        ...            "value_dimensions": [
        ...                {
        ...                    "column": "temp",
        ...                    "unit": "C"
        ...                }
        ...            ]
        ...        }
        ...    ]
        ... }
        >>> get_metric_info(multitsframe, "external_id")
        { "first": "external_first", "second": "external_second" }

    """
    spec = spec_by_metric_key(metric_info)
    metric_info = glom(multitsframe.attrs, spec)
    return defaultdict(lambda: None, metric_info)


def extract_series_metric_key(metadata: Any) -> Any:
    return glom(metadata, Coalesce("dataset_metadata.single_metric", default="series"))


def extract_from_metadata(metadata: Any, key: str, default: str | None = None) -> Any:
    return glom(metadata, Coalesce(f"dataset_metadata.{key}", default=default))


def get_series_info(series: pd.Series, value_dim_info: str | Spec) -> Any:
    """Get an arbitrary series info

    Since a series has only one value dimension named "value", this information is
    equivalent to information on the metric.

    Since the fallback behaviour for this value dimension is to fall back to the metric
    metadata, we can reuse the code that extracts value_dimension metadata for
    this value dimension.
    """
    series_metric_key = extract_from_metadata(series.attrs, key="single_metric", default="series")
    from_new_convention = get_value_dimension_info(series, value_dim_info)[series_metric_key].get('value')


    if from_new_convention is not None:
        return from_new_convention

    # compatibility with some older format
    return glom(
        series.attrs,
        Coalesce(
            spec_not_none(
                (
                    "single_metric_metadata.structured_metadata.value_dimensions.value",
                    value_dim_info,
                )
            ),
            spec_not_none(
                (
                    "single_metric_metadata.structured_metadata.metric",
                    value_dim_info,
                )
            ),
            default=None,
        ),
    )


def get_series_unit(series: pd.Series) -> str | None:
    """Gets name of the series from metadata

    Args:
        series (pd.Series): Series with metadata following the convention

    Returns:
        str | None:
            Returns the unit of series.
            If the unit of the series is not present it returns None.

    Raises:
        TypeError: If `series` is not a Series.

    .. doctest::

        >>> from hdhelpers.metadata import get_series_unit
        >>> attr = { "by_metric": { "series": {"value_dimensions": {}}}}
        >>> series = pd.Series()
        >>> series.attrs = attr
        >>> get_series_unit(series) is None
        True
        >>> from hdhelpers.metadata import get_series_unit
        >>> attr = { "by_metric": { "series": {"value_dimensions": {"value": {"unit":None}}}}}
        >>> series = pd.Series()
        >>> series.attrs = attr
        >>> get_series_unit(series) is None
        True
        >>> attr = { "by_metric": { "series": {"value_dimensions": {"value": {"unit":"m/s"}}}}}
        >>> series = pd.Series()
        >>> series.attrs = attr
        >>> get_series_unit(series)
        'm/s'
    """
    return cast(str | None, get_series_info(series, spec_not_none("unit")))


def get_series_name(series: pd.Series) -> str | None:
    """Gets name of the series from metadata

    Args:
        series (pd.Series): Series with metadata following the convention

    Returns:
        str | None:
            Returns the name of the value.
            If the name of the value is not present it returns the name of the metric.
            If the metric name is not present it returns None.

    Raises:
        TypeError: If `series` is not a Series.

    .. doctest::

        >>> from hdhelpers.metadata import get_series_name
        >>> attr = { "by_metric": { "series": {"value_dimensions": {"value": {"name": "value_name_of_series"}}}}}
        >>> series = pd.Series()
        >>> series.attrs = attr
        >>> get_series_name(series)
        'value_name_of_series'

        >>> attr = { "by_metric": { "series": {"metric": {"name": "name_of_series"}}}}
        >>> series = pd.Series()
        >>> series.attrs = attr
        >>> get_series_name(series)
        'name_of_series'

        >>> attr = { "by_metric": { "series": {"metric": {"name": "name_of_series"}},
        ...                                   "value_dimensions": {"value": {"name": "value_name_of_series"}}}}
        >>> series = pd.Series()
        >>> series.attrs = attr
        >>> get_series_name(series)
        'name_of_series'
    """
    return cast(str | None, get_series_info(series, spec_not_none("name")))


def get_series_display_name(series: pd.Series) -> str | None:
    """Gets display name of the series from metadata

    Args:
        series (pd.Series): Series with metadata following the convention

    Returns:
        str | None:
            Returns the display name of the value.
            If the display name of the value is not present it returns the display name of the metric.
            If the metric display name is not present it returns the result of get_series_name().

    Raises:
        TypeError: If `series` is not a Series.

    .. doctest::

        >>> from hdhelpers.metadata import get_series_display_name
        >>> attr = { "by_metric": { "series": {"metric": {"display_name": "display_name_of_series"}}}}
        >>> series = pd.Series()
        >>> series.attrs = attr
        >>> get_series_display_name(series)
        'display_name_of_series'
    """
    return cast(
        str | None,
        get_series_info(
            series,
            Coalesce(
                spec_not_none("display_name"),
                spec_not_none("name"),
                spec_not_none("short_display_name"),
            ),
        ),
    )


def get_series_short_display_name(series: pd.Series) -> str | None:
    """Gets short display name of the Series from metadata

    Args:
        series (pd.Series): Series with metadata following the convention

    Returns:
        str | None:
            Returns the short display name of the value.
            If the short display name of the value is not present it returns the short display name of the metric.
            If the metric short display name is not present it returns the result of series_display_name().

    Raises:
        TypeError: If `series` is not a Series.

    .. doctest::

        >>> from hdhelpers.metadata import get_series_short_display_name
        >>> attr = { "by_metric": { "series": { "metric": {"short_display_name": "short_display_name_of_series"}}}}
        >>> series = pd.Series()
        >>> series.attrs = attr
        >>> get_series_short_display_name(series)
        'short_display_name_of_series'
    """
    return cast(
        str | None,
        get_series_info(
            series,
            Coalesce(
                spec_not_none("short_display_name"),
                spec_not_none("display_name"),
                spec_not_none("name"),
            ),
        ),
    )


def get_series_measurement(series: pd.Series) -> str | None:
    return cast(str | None, get_series_info(series, "measurement"))


def get_queried_interval(
    data: pd.Series | pd.DataFrame,
) -> tuple[datetime.datetime | None, datetime.datetime | None]:
    start = extract_from_metadata(data.attrs, key="ref_interval_start_timestamp", default=None)
    end = extract_from_metadata(data.attrs, key="ref_interval_end_timestamp", default=None)

    formatted_start = datetime.datetime.fromisoformat(start) if start else None
    formatted_end = datetime.datetime.fromisoformat(end) if end else None

    return formatted_start, formatted_end
