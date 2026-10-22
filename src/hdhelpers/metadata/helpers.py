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

import hdhelpers.metadata._specs as _specs
from hdhelpers.metadata._current_convention import follows_current_convention
from hdhelpers.metadata._helpers import (
    check_dataframe,
    check_series,
    check_series_or_dataframe,
    default_timezone_by_metric,
    extract_from_metadata,
    get_value_dimension_info,
    metric_info_by_metric,
    singlets_metric_info,
    singlets_value_dimension_info,
    single_metric_default_timezone,
    singlets_value_dimension_info_with_fallbacks,
    spec_not_none,
    value_dimension_info_with_fallbacks,
)


def get_units(
    multitsframe: pd.DataFrame, *, include_inherited: bool = False
) -> defaultdict[str, defaultdict[str, str | None]]:
    """Gets unit of value dimensions in MTSF metrics from Metadata

    Args:
        multitsframe (pd.DataFrame): MTSF with metadata following the convention.
        include_inherited (bool): Whether to fall back to the properties a metric inherits from objects higher up in an asset hierarchy (given under "inherited" in the metric metadata) as last resort, i.e. if neither the value dimension, the metric nor "value_dimensions_shared" provide the information. Defaults to False, since this information should be provided for the metric itself.

    Returns:
        dict[str, dict[str | None] | None]: Dictionary of metrics containing the names of the value dimensions.
        If the short display name of the value_dimension is not present it returns the result of get_value_dimension_info().

    Raises:
        TypeError: If `multitsframe` is not a DataFrame.

    Code example:

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
    return get_value_dimension_info(multitsframe, _specs.UNIT, include_inherited)


def get_names(
    multitsframe: pd.DataFrame, *, include_inherited: bool = False
) -> defaultdict[str, defaultdict[str, str | None]]:
    """Gets names of the MTSF metrics from the metadata

    Args:
        multitsframe (pd.DataFrame): MTSF with metadata following the convention.
        include_inherited (bool): Whether to fall back to the properties a metric inherits from objects higher up in an asset hierarchy (given under "inherited" in the metric metadata) as last resort, i.e. if neither the value dimension, the metric nor "value_dimensions_shared" provide the information. Defaults to False, since this information should be provided for the metric itself.

    Returns:
        dict[str, str | None]: Dictionary of metrics containing the names. If the name is not present for a metric the corresponding value is None.

    Raises:
        TypeError: If `multitsframe` is not a DataFrame.

    Code example:

    .. doctest:: metadata.get_names

        >>> attr = { "by_metric": { "metric1": {"metric": {"name": "name_of_metric1"}},
        ...                        "metric2": {"metric": {"name": None }} }}
        >>> dataframe.attrs = attr
        >>> result = get_names(dataframe)
        >>> result["metric1"]["value"]
        'name_of_metric1'
        >>> result["metric2"]["value"] is None
        True

    Lets try another MTSF format:

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
    return get_value_dimension_info(multitsframe, _specs.NAME, include_inherited)


def get_display_names(
    multitsframe: pd.DataFrame, *, include_inherited: bool = False
) -> defaultdict[str, defaultdict[str, str | None]]:
    """Gets display names of the MTSF metrics from the metadata

    Args:
        multitsframe (pd.DataFrame): MTSF with metadata following the convention.
        include_inherited (bool): Whether to fall back to the properties a metric inherits from objects higher up in an asset hierarchy (given under "inherited" in the metric metadata) as last resort, i.e. if neither the value dimension, the metric nor "value_dimensions_shared" provide the information. Defaults to False, since this information should be provided for the metric itself.

    Returns:
        defaultdict[str, defaultdict[str, str | None]]: Dictionary of metrics containing the display names.
        If the display name of the metrics is not present it returns the result of :func:`hdhelpers.metadata.get_names`.
        For metadata following the current convention, the display name is looked up on the value dimension, on
        the metric (for the value dimension "value") and in "value_dimensions_shared" before falling back to the
        name. Fields provided as null count as missing.

    Raises:
        TypeError: If `multitsframe` is not a DataFrame.

    Code example:

    .. doctest:: metadata.get_display_names

        >>> attr = { "by_metric": { "metric1": {"metric": {"display_name": "display_name_of_metric1"}},
        ...                         "metric2": {"metric": {"name": "name_of_metric2"}}}}
        >>> dataframe.attrs = attr
        >>> result = get_display_names(dataframe)
        >>> result["metric1"]["value"]
        'display_name_of_metric1'
        >>> result["metric2"]["value"]
        'name_of_metric2'

    Lets try another MTSF format:

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
    return value_dimension_info_with_fallbacks(
        multitsframe, _specs.DISPLAY_NAME_FIELDS, _specs.DISPLAY_NAME, include_inherited
    )


def get_short_display_names(
    multitsframe: pd.DataFrame, *, include_inherited: bool = False
) -> defaultdict[str, defaultdict[str, str | None]]:
    """Gets short display names of the MTSF metrics from the metadata

    Args:
        multitsframe (pd.DataFrame): MTSF with metadata following the convention.
        include_inherited (bool): Whether to fall back to the properties a metric inherits from objects higher up in an asset hierarchy (given under "inherited" in the metric metadata) as last resort, i.e. if neither the value dimension, the metric nor "value_dimensions_shared" provide the information. Defaults to False, since this information should be provided for the metric itself.

    Returns:
        defaultdict[str, defaultdict[str, str | None]]: Dictionary of metrics containing the short display names.
        If the short display name of the metrics is not present it returns the result of :func:`hdhelpers.metadata.get_display_names`.
        For metadata following the current convention, each of short display name, display name and name is
        looked up on the value dimension, on the metric (for the value dimension "value") and in
        "value_dimensions_shared" before falling back to the next one. Fields provided as null count as missing.

    Raises:
        TypeError: If `multitsframe` is not a DataFrame.

    Code example:

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

    Lets try another MTSF format:

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
    return value_dimension_info_with_fallbacks(
        multitsframe, _specs.SHORT_DISPLAY_NAME_FIELDS, _specs.SHORT_DISPLAY_NAME, include_inherited
    )


def get_measurements(
    multitsframe: pd.DataFrame, *, include_inherited: bool = False
) -> defaultdict[str, defaultdict[str, str | None]]:
    """Gets measurement (type) of the MTSF metrics from the metadata

    Args:
        multitsframe (pd.DataFrame): MTSF with metadata following the convention.
        include_inherited (bool): Whether to fall back to the properties a metric inherits from objects higher up in an asset hierarchy (given under "inherited" in the metric metadata) as last resort, i.e. if neither the value dimension, the metric nor "value_dimensions_shared" provide the information. Defaults to False, since this information should be provided for the metric itself.

    Returns:
        defaultdict[str, defaultdict[str, str | None]]: Dictionary of metrics containing the measurement (type) of the MTSF metrics.
        If the short measurement (type) of the MTSF metrics is not present it returns None.

    Raises:
        TypeError: If `multitsframe` is not a DataFrame.

    Code example:

    .. doctest:: metadata.get_measurements

        >>> attr = { "dataset_metadata": {"metric_key": "external_id"},
        ...          "metrics": [{"external_id": "column_name", "value_dimensions": [{"column": "temp", "measurement": "temperature"}]}]}
        >>> dataframe.attrs = attr
        >>> result = get_measurements(dataframe)
        >>> result["column_name"]["temp"]
        'temperature'


    """
    check_dataframe(multitsframe)
    return get_value_dimension_info(multitsframe, _specs.MEASUREMENT, include_inherited)


def get_metric_info(
    multitsframe: pd.DataFrame, metric_info: str | Spec, *, include_inherited: bool = True
) -> defaultdict[str, Any]:
    """Gets a dictionary of metadata associated to metrics.

    In contrast to metadata associated to concrete value dimensions, this
    function abstracts access to metadata associated to the underlying metric.

    The information is looked up in the metric itself, then in its value dimension "value",
    then in "value_dimensions_shared" and finally in the properties the metric inherits from
    objects higher up in an asset hierarchy (given under "inherited" in the metric metadata),
    e.g. the latitude of the plant a sensor belongs to. The latter can be switched off via
    `include_inherited`. Information provided as null counts as missing. Note that in contrast
    to this function, the functions for dedicated information like :func:`get_units` or
    :func:`get_display_names` do not fall back to inherited properties by default.

    Args:
        multitsframe (pd.DataFrame): MTSF with metadata following the convention.
        metric_info (str | Spec): Information to retrieve, interpreted as a glom Spec: e.g. a field name, a dotted path like "sensor.manufacturer" into sub dictionaries or any other glom Spec. See "How to query nested information?" in the first steps.
        include_inherited (bool): Whether to fall back to the properties a metric inherits from objects higher up in an asset hierarchy (given under "inherited" in the metric metadata) as last resort, i.e. if neither the metric, its value dimension "value" nor "value_dimensions_shared" provide the information. Defaults to True.

    Returns:
        defaultdict[str, Any]: Dictionary, where keys are the entries of the metrics metadata specified via "metric_key" in "dataset_metadata" and values are the entries specified via "metric_info" in the metrics metadata. Defaults to None, also if there is no metric metadata at all.

    Code example:

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
        ...            "sensor": {"manufacturer": "Acme"},
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

    A dotted path reaches into sub dictionaries:

    .. doctest:: metadata.get_metric_info

        >>> result = get_metric_info(multitsframe, "sensor.manufacturer")
        >>> result["first"]
        'Acme'
        >>> result["second"] is None
        True
    """
    check_dataframe(multitsframe)
    return defaultdict(
        lambda: None, metric_info_by_metric(multitsframe, metric_info, include_inherited)
    )


def get_series_info(
    series: pd.Series, value_dim_info: str | Spec, *, include_inherited: bool = True
) -> Any:
    """Gets an arbitrary series info

    Since a series has only one value dimension named "value", this information is
    equivalent to information on the metric.

    Args:
        series (pd.Series): Series with metadata following the convention.
        value_dim_info (str | Spec): Information to retrieve, interpreted as a glom Spec: e.g. a field name, a dotted path like "sensor.manufacturer" into sub dictionaries or any other glom Spec. See "How to query nested information?" in the first steps.
        include_inherited (bool): Whether to fall back to the properties a metric inherits from objects higher up in an asset hierarchy (given under "inherited" in the metric metadata) as last resort, i.e. if neither the value dimension, the metric nor "value_dimensions_shared" provide the information. Defaults to True.

    Returns:
        Any: Retrieved information defined by `value_dim_info`

    Code example:

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
    from_new_convention = _series_value(
        get_value_dimension_info(series, value_dim_info, include_inherited), series
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


def _series_value(info_by_metric: dict, series: pd.Series) -> Any:
    """Info of the value dimension "value" of the metric of a Series

    The metric is identified via "single_metric" in "dataset_metadata", defaulting to "series"
    as used by older metadata structures. If it is not found but exactly one metric is present,
    that one is used, since a Series cannot be ambiguous in this respect.
    """
    series_metric_key = extract_from_metadata(series.attrs, key="single_metric", default="series")
    if series_metric_key in info_by_metric:
        return info_by_metric[series_metric_key].get("value")
    if len(info_by_metric) == 1:
        return next(iter(info_by_metric.values())).get("value")
    return None


def _series_info_with_fallbacks(
    series: pd.Series, fields: tuple[str, ...], include_inherited: bool
) -> Any:
    """Info of a Series, falling back to further fields

    For metadata following the current metadata convention, each field is looked up on the
    value dimension and the metric before the next field is tried, see
    value_dimension_info_with_fallbacks. Older metadata structures keep their established
    behaviour of using the first of the fields present on the first level providing any.
    """
    legacy_spec = Coalesce(*(spec_not_none(field) for field in fields))
    if follows_current_convention(series.attrs):
        return _series_value(
            value_dimension_info_with_fallbacks(series, fields, legacy_spec, include_inherited),
            series,
        )
    return get_series_info(series, legacy_spec, include_inherited=include_inherited)


def get_series_unit(series: pd.Series, *, include_inherited: bool = False) -> str | None:
    """Gets name of the series from metadata

    Args:
        series (pd.Series): Series with metadata following the convention.
        include_inherited (bool): Whether to fall back to the properties a metric inherits from objects higher up in an asset hierarchy (given under "inherited" in the metric metadata) as last resort, i.e. if neither the value dimension, the metric nor "value_dimensions_shared" provide the information. Defaults to False, since this information should be provided for the metric itself.

    Returns:
        str | None:
            Returns the unit of series.
            If the unit of the series is not present it returns None.

    Raises:
        TypeError: If `series` is not a Series.

    Let's test what happens if series has no attr:

    .. doctest:: metadata.get_series_unit

        >>> series.attrs = {}
        >>> get_series_unit(series) is None
        True

    Let's test what happens if series has attr but no entry for unit:

    .. doctest:: metadata.get_series_unit

        >>> attr = { "by_metric": { "series": {"value_dimensions": {"value": {"unit":None}}}}}
        >>> series.attrs = attr
        >>> get_series_unit(series) is None
        True

    Let's test what happens if series has unit in attr:

    .. doctest:: metadata.get_series_unit

        >>> attr = { "by_metric": { "series": {"value_dimensions": {"value": {"unit":"m/s"}}}}}
        >>> series.attrs = attr
        >>> get_series_unit(series)
        'm/s'
    """

    check_series(series)
    return cast(
        str | None,
        get_series_info(series, spec_not_none("unit"), include_inherited=include_inherited),
    )


def get_series_name(series: pd.Series, *, include_inherited: bool = False) -> str | None:
    """Gets name of the series from metadata

    Args:
        series (pd.Series): Series with metadata following the convention.
        include_inherited (bool): Whether to fall back to the properties a metric inherits from objects higher up in an asset hierarchy (given under "inherited" in the metric metadata) as last resort, i.e. if neither the value dimension, the metric nor "value_dimensions_shared" provide the information. Defaults to False, since this information should be provided for the metric itself.

    Returns:
        str | None:
            Returns the name of the value.
            If the name of the metric is not present it returns the name of the value.
            If the value name is not present it returns None.

    Raises:
        TypeError: If `series` is not a Series.

    Let's test what happens if series has name in value_dimensions:

    .. doctest:: metadata.get_series_name

        >>> attr = { "by_metric": { "series": {"value_dimensions": {"value": {"name": "value_name_of_series"}}}}}
        >>> series.attrs = attr
        >>> get_series_name(series)
        'value_name_of_series'

    Let's test what happens if series has name in metric:

    .. doctest:: metadata.get_series_name

        >>> attr = { "by_metric": { "series": {"metric": {"name": "name_of_series_1"}}}}
        >>> series.attrs = attr
        >>> get_series_name(series)
        'name_of_series_1'

    Let's test what happens if series has name in metric and value_dimensions:

    .. doctest:: metadata.get_series_name

        >>> attr = { "single_metric_metadata": { "structured_metadata": {"metric": {"name": "name_of_series_2"}},
        ...                                                              "value_dimensions": {"value": {"name": "value_name_of_series"}}}}
        >>> series.attrs = attr
        >>> get_series_name(series)
        'name_of_series_2'
    """
    check_series(series)
    return cast(
        str | None,
        get_series_info(series, spec_not_none("name"), include_inherited=include_inherited),
    )


def get_series_display_name(series: pd.Series, *, include_inherited: bool = False) -> str | None:
    """Gets display name of the series from metadata

    Args:
        series (pd.Series): Series with metadata following the convention.
        include_inherited (bool): Whether to fall back to the properties a metric inherits from objects higher up in an asset hierarchy (given under "inherited" in the metric metadata) as last resort, i.e. if neither the value dimension, the metric nor "value_dimensions_shared" provide the information. Defaults to False, since this information should be provided for the metric itself.

    Returns:
        str | None:
            Returns the display name of the value.
            If the display name of the metric is not present it returns the display name of the value.
            If the metric display name is not present it returns the result of :func:`hdhelpers.metadata.get_series_name`.

    Raises:
        TypeError: If `series` is not a Series.

    Code example:

    .. doctest:: metadata.get_series_display_name

        >>> attr = { "by_metric": { "series": {"metric": {"display_name": "display_name_of_series"}}}}
        >>> series.attrs = attr
        >>> get_series_display_name(series)
        'display_name_of_series'
    """
    check_series(series)
    return cast(
        str | None,
        _series_info_with_fallbacks(
            series, ("display_name", "name", "short_display_name"), include_inherited
        ),
    )


def get_series_short_display_name(
    series: pd.Series, *, include_inherited: bool = False
) -> str | None:
    """Gets short display name of the Series from metadata

    Args:
        series (pd.Series): Series with metadata following the convention.
        include_inherited (bool): Whether to fall back to the properties a metric inherits from objects higher up in an asset hierarchy (given under "inherited" in the metric metadata) as last resort, i.e. if neither the value dimension, the metric nor "value_dimensions_shared" provide the information. Defaults to False, since this information should be provided for the metric itself.

    Returns:
        str | None:
            Returns the short display name of the value.
            If the short display name of the metric is not present it returns the short display name of the value.
            If the metric short display name is not present it returns the result of :func:`hdhelpers.metadata.get_series_display_name`.

    Raises:
        TypeError: If `series` is not a Series.

    Code example:

    .. doctest:: metadata.get_series_short_display_name

        >>> attr = { "by_metric": { "series": { "metric": {"short_display_name": "short_display_name_of_series"}}}}
        >>> series.attrs = attr
        >>> get_series_short_display_name(series)
        'short_display_name_of_series'
    """
    check_series(series)
    return cast(
        str | None,
        _series_info_with_fallbacks(
            series, ("short_display_name", "display_name", "name"), include_inherited
        ),
    )


def get_series_measurement(series: pd.Series, *, include_inherited: bool = False) -> str | None:
    """Gets measurement (type) of the Series from metadata

    Args:
        series (pd.Series): Series with metadata following the convention.
        include_inherited (bool): Whether to fall back to the properties a metric inherits from objects higher up in an asset hierarchy (given under "inherited" in the metric metadata) as last resort, i.e. if neither the value dimension, the metric nor "value_dimensions_shared" provide the information. Defaults to False, since this information should be provided for the metric itself.

    Returns:
        str | None:
            Returns the  measurement (type) of the value.
            If "measurement" is not given in the metadata, None is returned.

    Raises:
        TypeError: If `series` is not a Series.

    Code example:

    .. doctest:: metadata.get_series_measurement

        >>> attr = { "by_metric": { "series": { "metric": {"measurement": "temperature"}}}}
        >>> series.attrs = attr
        >>> get_series_measurement(series)
        'temperature'
    """
    check_series(series)
    return cast(
        str | None, get_series_info(series, "measurement", include_inherited=include_inherited)
    )


def get_singlets_info(
    singletsframe: pd.DataFrame, value_dim_info: str | Spec, *, include_inherited: bool = True
) -> Any:
    """Gets an arbitrary info of the value dimensions of a SingleTSFrame

    A SingleTSFrame (STSF) holds exactly one metric - like a Series - but arbitrarily many
    value dimensions - like a MultiTSFrame. Therefore, in contrast to the MTSF functions,
    the result is keyed by value dimension only and not by metric first.

    The single metric is identified via "single_metric" in "dataset_metadata". If that is
    missing but the metadata contains exactly one metric, that metric is used, since a STSF
    cannot be ambiguous in this respect.

    Args:
        singletsframe (pd.DataFrame): STSF with metadata following the convention.
        value_dim_info (str | Spec): Information to retrieve, interpreted as a glom Spec: e.g. a field name, a dotted path like "sensor.manufacturer" into sub dictionaries or any other glom Spec. See "How to query nested information?" in the first steps.
        include_inherited (bool): Whether to fall back to the properties a metric inherits from objects higher up in an asset hierarchy (given under "inherited" in the metric metadata) as last resort, i.e. if neither the value dimension, the metric nor "value_dimensions_shared" provide the information. Defaults to True.

    Returns:
        defaultdict[str, Any]: Dictionary of value dimensions containing the retrieved information. If the information is not present for a value dimension the corresponding value is None.

    Raises:
        TypeError: If `singletsframe` is not a DataFrame.

    Code example:

    .. doctest:: metadata.get_singlets_info

        >>> dataframe.attrs = {
        ...     "dataset_metadata": {"single_metric": "abc.temp", "metric_key": "external_id"},
        ...     "metrics": [
        ...         {
        ...             "external_id": "abc.temp",
        ...             "value_dimensions": [
        ...                 {"column": "value", "unit": "°C"},
        ...                 {"column": "state"},
        ...             ],
        ...         }
        ...     ],
        ... }
        >>> result = get_singlets_info(dataframe, "unit")
        >>> result["value"]
        '°C'
        >>> result["state"] is None
        True
    """

    check_dataframe(singletsframe)
    return singlets_value_dimension_info(singletsframe, value_dim_info, include_inherited)


def get_singlets_units(
    singletsframe: pd.DataFrame, *, include_inherited: bool = False
) -> defaultdict[str, str | None]:
    """Gets units of the value dimensions of a SingleTSFrame from metadata

    Args:
        singletsframe (pd.DataFrame): STSF with metadata following the convention.
        include_inherited (bool): Whether to fall back to the properties a metric inherits from objects higher up in an asset hierarchy (given under "inherited" in the metric metadata) as last resort, i.e. if neither the value dimension, the metric nor "value_dimensions_shared" provide the information. Defaults to False, since this information should be provided for the metric itself.

    Returns:
        defaultdict[str, str | None]: Dictionary of value dimensions containing the units. If the unit is not present for a value dimension the corresponding value is None.

    Raises:
        TypeError: If `singletsframe` is not a DataFrame.

    Note that a value dimension falls back to "value_dimensions_shared" if it carries no unit
    of its own:

    .. doctest:: metadata.get_singlets_units

        >>> dataframe.attrs = {
        ...     "dataset_metadata": {"single_metric": "abc.temp", "metric_key": "external_id"},
        ...     "metrics": [
        ...         {
        ...             "external_id": "abc.temp",
        ...             "value_dimensions": [
        ...                 {"column": "value", "unit": "°C"},
        ...                 {"column": "state"},
        ...             ],
        ...         }
        ...     ],
        ...     "value_dimensions_shared": [{"column": "state", "unit": "UNKNOWN"}],
        ... }
        >>> result = get_singlets_units(dataframe)
        >>> result["value"]
        '°C'
        >>> result["state"]
        'UNKNOWN'
        >>> result["not-given"] is None
        True

    The "metric_key" is optional and defaults to "id":

    .. doctest:: metadata.get_singlets_units

        >>> dataframe.attrs = {
        ...     "dataset_metadata": {"single_metric": "abc.temp"},
        ...     "metrics": [
        ...         {"id": "abc.temp", "value_dimensions": [{"column": "value", "unit": "m"}]}
        ...     ],
        ... }
        >>> get_singlets_units(dataframe)["value"]
        'm'
    """

    check_dataframe(singletsframe)
    return singlets_value_dimension_info(singletsframe, _specs.UNIT, include_inherited)


def get_singlets_names(
    singletsframe: pd.DataFrame, *, include_inherited: bool = False
) -> defaultdict[str, str | None]:
    """Gets names of the value dimensions of a SingleTSFrame from metadata

    Args:
        singletsframe (pd.DataFrame): STSF with metadata following the convention.
        include_inherited (bool): Whether to fall back to the properties a metric inherits from objects higher up in an asset hierarchy (given under "inherited" in the metric metadata) as last resort, i.e. if neither the value dimension, the metric nor "value_dimensions_shared" provide the information. Defaults to False, since this information should be provided for the metric itself.

    Returns:
        defaultdict[str, str | None]: Dictionary of value dimensions containing the names. If the name is not present for a value dimension the corresponding value is None.

    Raises:
        TypeError: If `singletsframe` is not a DataFrame.

    Code example:

    .. doctest:: metadata.get_singlets_names

        >>> dataframe.attrs = {
        ...     "dataset_metadata": {"single_metric": "abc.temp", "metric_key": "external_id"},
        ...     "metrics": [
        ...         {
        ...             "external_id": "abc.temp",
        ...             "value_dimensions": [
        ...                 {"column": "value", "name": "temperature"},
        ...                 {"column": "state"},
        ...             ],
        ...         }
        ...     ],
        ... }
        >>> result = get_singlets_names(dataframe)
        >>> result["value"]
        'temperature'
        >>> result["state"] is None
        True
    """

    check_dataframe(singletsframe)
    return singlets_value_dimension_info(singletsframe, _specs.NAME, include_inherited)


def get_singlets_display_names(
    singletsframe: pd.DataFrame, *, include_inherited: bool = False
) -> defaultdict[str, str | None]:
    """Gets display names of the value dimensions of a SingleTSFrame from metadata

    Falls back to the name of the value dimension if no display name is given. The display name
    is looked up on the value dimension, on the metric (for the value dimension "value") and in
    "value_dimensions_shared" before falling back to the name. Fields provided as null count as
    missing.

    Args:
        singletsframe (pd.DataFrame): STSF with metadata following the convention.
        include_inherited (bool): Whether to fall back to the properties a metric inherits from objects higher up in an asset hierarchy (given under "inherited" in the metric metadata) as last resort, i.e. if neither the value dimension, the metric nor "value_dimensions_shared" provide the information. Defaults to False, since this information should be provided for the metric itself.

    Returns:
        defaultdict[str, str | None]: Dictionary of value dimensions containing the display names. If neither display name nor name is present for a value dimension the corresponding value is None.

    Raises:
        TypeError: If `singletsframe` is not a DataFrame.

    Code example:

    .. doctest:: metadata.get_singlets_display_names

        >>> dataframe.attrs = {
        ...     "dataset_metadata": {"single_metric": "abc.temp", "metric_key": "external_id"},
        ...     "metrics": [
        ...         {
        ...             "external_id": "abc.temp",
        ...             "value_dimensions": [
        ...                 {"column": "value", "name": "temperature", "display_name": "temp"},
        ...                 {"column": "state", "name": "measurement state"},
        ...             ],
        ...         }
        ...     ],
        ... }
        >>> result = get_singlets_display_names(dataframe)
        >>> result["value"]
        'temp'
        >>> result["state"]
        'measurement state'
    """

    check_dataframe(singletsframe)
    return singlets_value_dimension_info_with_fallbacks(
        singletsframe, _specs.DISPLAY_NAME_FIELDS, _specs.DISPLAY_NAME, include_inherited
    )


def get_singlets_short_display_names(
    singletsframe: pd.DataFrame, *, include_inherited: bool = False
) -> defaultdict[str, str | None]:
    """Gets short display names of the value dimensions of a SingleTSFrame from metadata

    Falls back to the display name and then to the name of the value dimension if no short
    display name is given. Each of them is looked up on the value dimension, on the metric (for
    the value dimension "value") and in "value_dimensions_shared" before falling back to the next
    one. Fields provided as null count as missing.

    Args:
        singletsframe (pd.DataFrame): STSF with metadata following the convention.
        include_inherited (bool): Whether to fall back to the properties a metric inherits from objects higher up in an asset hierarchy (given under "inherited" in the metric metadata) as last resort, i.e. if neither the value dimension, the metric nor "value_dimensions_shared" provide the information. Defaults to False, since this information should be provided for the metric itself.

    Returns:
        defaultdict[str, str | None]: Dictionary of value dimensions containing the short display names. If none of short display name, display name and name is present for a value dimension the corresponding value is None.

    Raises:
        TypeError: If `singletsframe` is not a DataFrame.

    Code example:

    .. doctest:: metadata.get_singlets_short_display_names

        >>> dataframe.attrs = {
        ...     "dataset_metadata": {"single_metric": "abc.temp", "metric_key": "external_id"},
        ...     "metrics": [
        ...         {
        ...             "external_id": "abc.temp",
        ...             "value_dimensions": [
        ...                 {"column": "value", "name": "temperature", "short_display_name": "T"},
        ...                 {"column": "state", "display_name": "state"},
        ...             ],
        ...         }
        ...     ],
        ... }
        >>> result = get_singlets_short_display_names(dataframe)
        >>> result["value"]
        'T'
        >>> result["state"]
        'state'
    """

    check_dataframe(singletsframe)
    return singlets_value_dimension_info_with_fallbacks(
        singletsframe,
        _specs.SHORT_DISPLAY_NAME_FIELDS,
        _specs.SHORT_DISPLAY_NAME,
        include_inherited,
    )


def get_singlets_measurements(
    singletsframe: pd.DataFrame, *, include_inherited: bool = False
) -> defaultdict[str, str | None]:
    """Gets measurements (types) of the value dimensions of a SingleTSFrame from metadata

    Args:
        singletsframe (pd.DataFrame): STSF with metadata following the convention.
        include_inherited (bool): Whether to fall back to the properties a metric inherits from objects higher up in an asset hierarchy (given under "inherited" in the metric metadata) as last resort, i.e. if neither the value dimension, the metric nor "value_dimensions_shared" provide the information. Defaults to False, since this information should be provided for the metric itself.

    Returns:
        defaultdict[str, str | None]: Dictionary of value dimensions containing the measurements. If "measurement" is not given for a value dimension the corresponding value is None.

    Raises:
        TypeError: If `singletsframe` is not a DataFrame.

    Code example:

    .. doctest:: metadata.get_singlets_measurements

        >>> dataframe.attrs = {
        ...     "dataset_metadata": {"single_metric": "abc.temp", "metric_key": "external_id"},
        ...     "metrics": [
        ...         {
        ...             "external_id": "abc.temp",
        ...             "value_dimensions": [
        ...                 {"column": "value", "measurement": "temperature"},
        ...             ],
        ...         }
        ...     ],
        ... }
        >>> get_singlets_measurements(dataframe)["value"]
        'temperature'
    """

    check_dataframe(singletsframe)
    return singlets_value_dimension_info(singletsframe, _specs.MEASUREMENT, include_inherited)


def get_singlets_metric_info(
    singletsframe: pd.DataFrame, metric_info: str | Spec, *, include_inherited: bool = True
) -> Any:
    """Gets metadata associated to the single metric of a SingleTSFrame

    Counterpart of :func:`get_metric_info` for SingleTSFrames: instead of a dictionary keyed
    by metric this directly returns the requested information for the one metric. Like
    :func:`get_metric_info`, it falls back to the value dimension "value", to
    "value_dimensions_shared" and finally to the properties the metric inherits.

    Args:
        singletsframe (pd.DataFrame): STSF with metadata following the convention.
        metric_info (str | Spec): Information to retrieve, interpreted as a glom Spec: e.g. a field name, a dotted path like "sensor.manufacturer" into sub dictionaries or any other glom Spec. See "How to query nested information?" in the first steps.
        include_inherited (bool): Whether to fall back to the properties a metric inherits from objects higher up in an asset hierarchy (given under "inherited" in the metric metadata) as last resort, i.e. if neither the metric, its value dimension "value" nor "value_dimensions_shared" provide the information. Defaults to True.

    Returns:
        Any: Retrieved information defined by `metric_info`, or None if it cannot be determined - which includes the case of absent metric metadata.

    Raises:
        TypeError: If `singletsframe` is not a DataFrame.

    Code example:

    .. doctest:: metadata.get_singlets_metric_info

        >>> dataframe.attrs = {
        ...     "dataset_metadata": {"single_metric": "abc.temp", "metric_key": "external_id"},
        ...     "metrics": [{"external_id": "abc.temp", "name": "ABC temperature"}],
        ... }
        >>> get_singlets_metric_info(dataframe, "name")
        'ABC temperature'
        >>> get_singlets_metric_info(dataframe, "not-given") is None
        True

    Without any metadata None is returned:

    .. doctest:: metadata.get_singlets_metric_info

        >>> dataframe.attrs = {}
        >>> get_singlets_metric_info(dataframe, "name") is None
        True
    """

    check_dataframe(singletsframe)
    return singlets_metric_info(singletsframe, metric_info, include_inherited)


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

    Code example:

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


def get_default_timezones(multitsframe: pd.DataFrame) -> defaultdict[str, str | None]:
    """Gets the default time zone of each metric of a MultiTSFrame

    The default time zone is meant for computations: It is the time zone the timeseries should
    be evaluated in by default, e.g. for bucketing days when aggregating, so that each day
    starts at midnight of this time zone. It belongs to the data, e.g. it is the time zone of
    the plant a sensor belongs to. It is not meant for displaying timestamps - that is what the
    time zone of the plot target settings is for, which e.g. :func:`hdhelpers.helpers.modify_timezone`
    uses by default. See "Which time zone to compute in?" in the first steps.

    The time zone is an IANA time zone name like "Europe/Berlin" or a fixed UTC offset like
    "+02:00", both accepted by pandas, e.g. by ``tz_convert``.

    The default time zone of a metric falls back to the one of the dataset metadata, which
    applies to all metrics without their own. As specified by the metadata conventions, it does
    not fall back to value dimensions or inherited properties.

    Args:
        multitsframe (pd.DataFrame): MTSF with metadata following the convention.

    Returns:
        defaultdict[str, str | None]: Dictionary, where keys are the entries of the metrics metadata specified via "metric_key" in "dataset_metadata" and values are their default time zones. Defaults to the default time zone of the dataset metadata, also for metrics without metadata, and to None if that is missing as well.

    Raises:
        TypeError: If `multitsframe` is not a DataFrame.

    Code example:

    .. doctest:: metadata.get_default_timezones

        >>> multitsframe.attrs = {
        ...     "dataset_metadata": {"metric_key": "id", "default_timezone": "Europe/Berlin"},
        ...     "metrics": [
        ...         {"id": "new_york_sensor", "default_timezone": "America/New_York"},
        ...         {"id": "berlin_sensor"},
        ...     ],
        ... }
        >>> timezones = get_default_timezones(multitsframe)
        >>> timezones["new_york_sensor"]
        'America/New_York'
        >>> timezones["berlin_sensor"]
        'Europe/Berlin'
        >>> timezones["metric_without_metadata"]
        'Europe/Berlin'
    """
    check_dataframe(multitsframe)
    return default_timezone_by_metric(multitsframe)


def get_series_default_timezone(series: pd.Series) -> str | None:
    """Gets the default time zone of a Series

    The default time zone is meant for computations: It is the time zone the timeseries should
    be evaluated in by default, e.g. for bucketing days when aggregating, so that each day
    starts at midnight of this time zone. It belongs to the data, e.g. it is the time zone of
    the plant a sensor belongs to. It is not meant for displaying timestamps - that is what the
    time zone of the plot target settings is for, which e.g. :func:`hdhelpers.helpers.modify_timezone`
    uses by default. See "Which time zone to compute in?" in the first steps.

    The time zone is an IANA time zone name like "Europe/Berlin" or a fixed UTC offset like
    "+02:00", both accepted by pandas, e.g. by ``tz_convert``.

    The default time zone of the metric falls back to the one of the dataset metadata.

    Args:
        series (pd.Series): Series with metadata following the convention.

    Returns:
        str | None: The default time zone, or None if neither the metric nor the dataset metadata provide one.

    Raises:
        TypeError: If `series` is not a Series.

    Code example:

    .. doctest:: metadata.get_series_default_timezone

        >>> series.attrs = {
        ...     "dataset_metadata": {"single_metric": "water.north.level", "metric_key": "external_id"},
        ...     "metrics": [{"external_id": "water.north.level", "default_timezone": "Europe/Berlin"}],
        ... }
        >>> get_series_default_timezone(series)
        'Europe/Berlin'
        >>> series.attrs = {}
        >>> get_series_default_timezone(series) is None
        True
    """
    check_series(series)
    return single_metric_default_timezone(series)


def get_singlets_default_timezone(singletsframe: pd.DataFrame) -> str | None:
    """Gets the default time zone of the single metric of a SingleTSFrame

    The default time zone is meant for computations: It is the time zone the timeseries should
    be evaluated in by default, e.g. for bucketing days when aggregating, so that each day
    starts at midnight of this time zone. It belongs to the data, e.g. it is the time zone of
    the plant a sensor belongs to. It is not meant for displaying timestamps - that is what the
    time zone of the plot target settings is for, which e.g. :func:`hdhelpers.helpers.modify_timezone`
    uses by default. See "Which time zone to compute in?" in the first steps.

    The time zone is an IANA time zone name like "Europe/Berlin" or a fixed UTC offset like
    "+02:00", both accepted by pandas, e.g. by ``tz_convert``.

    The default time zone of the metric falls back to the one of the dataset metadata.

    Args:
        singletsframe (pd.DataFrame): STSF with metadata following the convention.

    Returns:
        str | None: The default time zone, or None if neither the metric nor the dataset metadata provide one.

    Raises:
        TypeError: If `singletsframe` is not a DataFrame.

    Code example:

    .. doctest:: metadata.get_singlets_default_timezone

        >>> dataframe.attrs = {
        ...     "dataset_metadata": {"single_metric": "abc.temp", "default_timezone": "+02:00"},
        ...     "metrics": [{"id": "abc.temp", "default_timezone": None}],
        ... }
        >>> get_singlets_default_timezone(dataframe)
        '+02:00'
    """
    check_dataframe(singletsframe)
    return single_metric_default_timezone(singletsframe)
