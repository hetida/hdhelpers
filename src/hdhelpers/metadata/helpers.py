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
    check_dataframe,
    check_series,
    check_series_or_dataframe,
    extract_from_metadata,
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



    .. doctest:: metadata.get_units

        >>> attr = {
        ...    "by_metric": {
        ...        "metric1": {
        ...           "value_dimensions": {
        ...                "value_dim_1": {
        ...                    "unit": "m"
        ...                }
        ...            }
        ...        },
        ...        "metric3": {
        ...            "value_dimensions": {
        ...                 "value_dim_1": {
        ...                     "unit": None,
        ...                 }
        ...            }
        ...        }
        ...    }
        ... }
        >>> dataframe.attrs = attr
        >>> result = get_units(dataframe)
        >>> result["metric1"]['value_dim_1']
        'm'
        >>> result["metric3"]['value_dim_1'] is None
        True
        >>> result["metric2"]['value_dim_1'] is None
        True
    """

    check_dataframe(multitsframe)
    return get_value_dimension_info(multitsframe, "unit")


def get_names(multitsframe: pd.DataFrame) -> defaultdict[str, defaultdict[str, str | None]]:
    """Gets names of the MTS metrics from Metadata

    Args:
        multitsframe (pd.DataFrame): MTS with metadata following the convention.

    Returns:
        dict[str, str | None]: Dictionary of metrics containing the names. If the name is not present for a metric the corresponding value is None.

    Raises:
        TypeError: If `multitsframe` is not a DataFrame.

    .. doctest:: metadata.get_names

        >>> attr = { "by_metric": { "metric1": {"metric": {"name": "name_of_metric1"}},
        ...                        "metric2": {"metric": {"name": None }} }}
        >>> dataframe.attrs = attr
        >>> result = get_names(dataframe)
        >>> result["metric1"]["value"]
        'name_of_metric1'
        >>> result["metric2"]["value"] is None
        True

    Lets try another MTS format

    .. doctest:: metadata.get_names

        >>> attr = { "dataset_metadata": {"metric_key": "external_id"},
        ...          "metrics": [{"external_id": "ruhr-temperature",
        ...                       "name": "Ruhr temperature [°C]",
        ...                       "display_name": "temperature [°C]",
        ...                       "short_display_name": "[°C]",
        ...                       "value_dimensions": [{"column": "temp", "measurement": "temperature", "unit": "°C"}]}]}
        >>> dataframe.attrs = attr
        >>> result = get_names(dataframe)
        >>> result["ruhr-temperature"]["value"]
        'Ruhr temperature [°C]'
    """

    check_dataframe(multitsframe)
    return get_value_dimension_info(multitsframe, Coalesce("name", default=None))


def get_display_names(multitsframe: pd.DataFrame) -> defaultdict[str, defaultdict[str, str | None]]:
    """Gets display names of the MTS metrics from the metadata

    Args:
        multitsframe (pd.DataFrame): MTS with metadata following the convention.

    Returns:
        defaultdict[str, defaultdict[str, str | None]]: Dictionary of metrics containing the display names.
        If the display name of the metrics is not present it returns the result of :func:`hdhelpers.metadata.get_names`.

    Raises:
        TypeError: If `multitsframe` is not a DataFrame.

    .. doctest:: metadata.get_display_names

        >>> attr = { "by_metric": { "metric1": {"metric": {"display_name": "display_name_of_metric1"}},
        ...                         "metric2": {"metric": {"name": "name_of_metric2"}}}}
        >>> dataframe.attrs = attr
        >>> result = get_display_names(dataframe)
        >>> result["metric1"]["value"]
        'display_name_of_metric1'
        >>> result["metric2"]["value"]
        'name_of_metric2'

    Lets try another MTS format

    .. doctest:: metadata.get_display_names

        >>> attr = { "dataset_metadata": {"metric_key": "external_id"},
        ...          "metrics": [{"external_id": "ruhr-temperature",
        ...                       "name": "Ruhr temperature [°C]",
        ...                       "display_name": "temperature [°C]",
        ...                       "short_display_name": "[°C]",
        ...                       "value_dimensions": [{"column": "temp", "measurement": "temperature", "unit": "°C"}]}]}
        >>> dataframe.attrs = attr
        >>> result = get_display_names(dataframe)
        >>> result["ruhr-temperature"]["value"]
        'temperature [°C]'
    """

    check_dataframe(multitsframe)
    return get_value_dimension_info(multitsframe, Coalesce("display_name", "name", default=None))


def get_short_display_names(
    multitsframe: pd.DataFrame,
) -> defaultdict[str, defaultdict[str, str | None]]:
    """Gets short display names of the MTS metrics from the metadata

    Args:
        multitsframe (pd.DataFrame): MTS with metadata following the convention.

    Returns:
        defaultdict[str, defaultdict[str, str | None]]: Dictionary of metrics containing the short display names.
        If the short display name of the metrics is not present it returns the result of :func:`hdhelpers.metadata.get_display_names`.

    Raises:
        TypeError: If `multitsframe` is not a DataFrame.

    .. doctest:: metadata.get_short_display_names

        >>> attr = { "by_metric": { "metric1": {"metric": {"short_display_name": "short_display_name_of_metric1"}},
        ...                         "metric2": {"metric": {"name": "name_of_metric2"}},
        ...                         "metric3": {"metric": {"name": None}} }}
        >>> dataframe.attrs = attr
        >>> result = get_short_display_names(dataframe)
        >>> result["metric1"]["value"]
        'short_display_name_of_metric1'
        >>> result["metric2"]["value"]
        'name_of_metric2'
        >>> result["metric3"]["value"] is None
        True

    Lets try another MTS format

    .. doctest:: metadata.get_short_display_names

        >>> attr = { "dataset_metadata": {"metric_key": "external_id"},
        ...          "metrics": [{"external_id": "ruhr-temperature",
        ...                       "name": "Ruhr temperature [°C]",
        ...                       "display_name": "temperature [°C]",
        ...                       "short_display_name": "temp. [°C]",
        ...                       "value_dimensions": [{"column": "temp", "measurement": "temperature", "unit": "°C"}]}]}
        >>> dataframe.attrs = attr
        >>> result = get_short_display_names(dataframe)
        >>> result["ruhr-temperature"]["value"]
        'temp. [°C]'
    """

    check_dataframe(multitsframe)
    return get_value_dimension_info(
        multitsframe, Coalesce("short_display_name", "display_name", "name", default=None)
    )


def get_measurements(multitsframe: pd.DataFrame) -> defaultdict[str, defaultdict[str, str | None]]:
    """Gets measurement (type) of the MTS metrics from the metadata

    Args:
        multitsframe (pd.DataFrame): MTS with metadata following the convention.

    Returns:
        defaultdict[str, defaultdict[str, str | None]]: Dictionary of metrics containing the measurement (type) of the MTS metrics.
        If the short measurement (type) of the MTS metrics is not present it returns None.

    Raises:
        TypeError: If `multitsframe` is not a DataFrame.

    .. doctest:: metadata.get_measurements

        >>> attr = { "dataset_metadata": {"metric_key": "external_id"},
        ...          "metrics": [{"external_id": "column_name", "value_dimensions": [{"column": "temp", "measurement": "temperature"}]}]}
        >>> dataframe.attrs = attr
        >>> result = get_measurements(dataframe)
        >>> result["column_name"]["temp"]
        'temperature'


    """
    check_dataframe(multitsframe)
    return get_value_dimension_info(multitsframe, "measurement")


def get_metric_info(multitsframe: pd.DataFrame, metric_info: str | Spec) -> defaultdict[str, Any]:
    """Get a dictionary of metadata associated to metrics

    In contrast to metadata associated to concrete value dimensions, this
    function abstracts access to metadata associated to the underlying metric.

    Args:
        multitsframe (pd.DataFrame): MTS with metadata following the convention.
        metric_info (str | Spec): Name of information to retrieve. Note that metric_info is interpreted as a glom Spec.

    Returns:
        defaultdict[str, Any]: dictionary, where keys are the entries of the metrics metadata specified via "metric_key" in "dataset_metadata" and values are the entries specified via "metric_info" in the metrics metadata

    .. doctest:: metadata.get_metric_info

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
        >>> result = get_metric_info(multitsframe, "external_id")
        >>> result["first"]
        'external_first'
        >>> result["second"]
        'external_second'
        >>> result["not-given"] is None
        True
    """
    check_dataframe(multitsframe)
    spec = spec_by_metric_key(metric_info)
    metric_info = glom(multitsframe.attrs, spec)
    return defaultdict(lambda: None, metric_info)


def get_series_info(series: pd.Series, value_dim_info: str | Spec) -> Any:
    """Get an arbitrary series info

    Since a series has only one value dimension named "value", this information is
    equivalent to information on the metric.

    Args:
        series (pd.Series): Series with metadata following the convention.
        value_dim_info (str | Spec): Name of information to retrieve. Note that `value_dim_info` is interpreted as a glom Spec.

    Returns:
        Any: Retrieved information defined by `value_dim_info`


    .. doctest:: metadata.get_series_info

        >>> attr = { "by_metric": { "series": {"value_dimensions": {"value": {"unit": "m"}}}}}
        >>> series.attrs = attr
        >>> get_series_info(series, "unit")
        'm'
        >>> get_series_info(series, "not-given") is None
        True
    """

    # Since the fallback behaviour for this value dimension is to fall back to the metric
    # metadata, we can reuse the code that extracts value_dimension metadata for
    # this value dimension.
    check_series(series)
    series_metric_key = extract_from_metadata(series.attrs, key="single_metric", default="series")
    from_new_convention = get_value_dimension_info(series, value_dim_info)[series_metric_key].get(
        "value"
    )

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
        series (pd.Series): Series with metadata following the convention.

    Returns:
        str | None:
            Returns the unit of series.
            If the unit of the series is not present it returns None.

    Raises:
        TypeError: If `series` is not a Series.

    Let's test what happens if series has no attr.

    .. doctest:: metadata.get_series_unit

        >>> series.attrs = {}
        >>> get_series_unit(series) is None
        True

    Let's test what happens if series has attr but no entry for unit.

    .. doctest:: metadata.get_series_unit

        >>> attr = { "by_metric": { "series": {"value_dimensions": {"value": {"unit":None}}}}}
        >>> series.attrs = attr
        >>> get_series_unit(series) is None
        True

    Let's test what happens if series has unit in attr.

    .. doctest:: metadata.get_series_unit

        >>> attr = { "by_metric": { "series": {"value_dimensions": {"value": {"unit":"m/s"}}}}}
        >>> series.attrs = attr
        >>> get_series_unit(series)
        'm/s'
    """

    check_series(series)
    return cast(str | None, get_series_info(series, spec_not_none("unit")))


def get_series_name(series: pd.Series) -> str | None:
    """Gets name of the series from metadata

    Args:
        series (pd.Series): Series with metadata following the convention.

    Returns:
        str | None:
            Returns the name of the value.
            If the name of the metric is not present it returns the name of the value.
            If the value name is not present it returns None.

    Raises:
        TypeError: If `series` is not a Series.

    Let's test what happens if series has name in value_dimensions.

    .. doctest:: metadata.get_series_name

        >>> attr = { "by_metric": { "series": {"value_dimensions": {"value": {"name": "value_name_of_series"}}}}}
        >>> series.attrs = attr
        >>> get_series_name(series)
        'value_name_of_series'

    Let's test what happens if series has name in metric.

    .. doctest:: metadata.get_series_name

        >>> attr = { "by_metric": { "series": {"metric": {"name": "name_of_series_1"}}}}
        >>> series.attrs = attr
        >>> get_series_name(series)
        'name_of_series_1'

    Let's test what happens if series has name in metric and value_dimensions.

    .. doctest:: metadata.get_series_name

        >>> attr = { "single_metric_metadata": { "structured_metadata": {"metric": {"name": "name_of_series_2"}},
        ...                                                              "value_dimensions": {"value": {"name": "value_name_of_series"}}}}
        >>> series.attrs = attr
        >>> get_series_name(series)
        'name_of_series_2'
    """
    check_series(series)
    return cast(str | None, get_series_info(series, spec_not_none("name")))


def get_series_display_name(series: pd.Series) -> str | None:
    """Gets display name of the series from metadata

    Args:
        series (pd.Series): Series with metadata following the convention.

    Returns:
        str | None:
            Returns the display name of the value.
            If the display name of the metric is not present it returns the display name of the value.
            If the metric display name is not present it returns the result of :func:`hdhelpers.metadata.get_series_name`.

    Raises:
        TypeError: If `series` is not a Series.

    .. doctest:: metadata.get_series_display_name

        >>> attr = { "by_metric": { "series": {"metric": {"display_name": "display_name_of_series"}}}}
        >>> series.attrs = attr
        >>> get_series_display_name(series)
        'display_name_of_series'
    """
    check_series(series)
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
        series (pd.Series): Series with metadata following the convention.

    Returns:
        str | None:
            Returns the short display name of the value.
            If the short display name of the metric is not present it returns the short display name of the value.
            If the metric short display name is not present it returns the result of :func:`hdhelpers.metadata.get_series_display_name`.

    Raises:
        TypeError: If `series` is not a Series.

    .. doctest:: metadata.get_series_short_display_name

        >>> attr = { "by_metric": { "series": { "metric": {"short_display_name": "short_display_name_of_series"}}}}
        >>> series.attrs = attr
        >>> get_series_short_display_name(series)
        'short_display_name_of_series'
    """
    check_series(series)
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
    """Gets measurement (type) of the Series from metadata

    Args:
        series (pd.Series): Series with metadata following the convention.

    Returns:
        str | None:
            Returns the  measurement (type) of the value.
            If "measurement" is not given in the metadata, None is returned.

    Raises:
        TypeError: If `series` is not a Series.

    .. doctest:: metadata.get_series_measurement

        >>> attr = { "by_metric": { "series": { "metric": {"measurement": "temperature"}}}}
        >>> series.attrs = attr
        >>> get_series_measurement(series)
        'temperature'
    """
    check_series(series)
    return cast(str | None, get_series_info(series, "measurement"))


def get_queried_interval(
    data: pd.Series | pd.DataFrame,
) -> tuple[datetime.datetime | None, datetime.datetime | None]:
    """Get queried interval from metadata

    Args:
        data (pd.Series | pd.DataFrame): Series or Dataframe with metadata following the convention

    Returns:
        tuple[datetime.datetime | None, datetime.datetime | None]: Tuple of available start and end date of requested interval.

    Raises:
        ValueError: If metadata of `data` is not None and not convertible to a datetime-object (ISO-format is expected).
        TypeError: If `data` is not a Series or Dataframe.

    .. doctest:: metadata.get_queried_interval

        >>> attr = {
        ...        "dataset_metadata": {
        ...        "ref_interval_start_timestamp": "2025-11-05T13:28:00Z",
        ...        "ref_interval_end_timestamp": "2025-11-06T13:28:00Z"
        ...    }
        ... }
        >>> series.attrs = attr
        >>> start, end = get_queried_interval(series)
        >>> start.isoformat()
        '2025-11-05T13:28:00+00:00'
        >>> end.isoformat()
        '2025-11-06T13:28:00+00:00'
    """
    check_series_or_dataframe(data)
    start = extract_from_metadata(data.attrs, key="ref_interval_start_timestamp", default=None)
    end = extract_from_metadata(data.attrs, key="ref_interval_end_timestamp", default=None)

    formatted_start = datetime.datetime.fromisoformat(start) if start else None
    formatted_end = datetime.datetime.fromisoformat(end) if end else None

    return formatted_start, formatted_end
