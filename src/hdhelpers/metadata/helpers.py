"""Functions accessing the metadata of SERIES, SINGLETSFRAMEs and MULTITSFRAMEs

The functions are thin wrappers over the methods of the models of the metadata conventions,
see read_metadata. The methods resolve the fallbacks of the conventions, e.g. a missing display
name falls back to the name, see hdhelpers.metadata._reading.

The metadata is the model attached to the object (see attach_metadata), whatever data type it
belongs to, e.g. the metadata of a SINGLETSFRAME on a Series taken from it. Otherwise the
metadata in attrs is parsed as the data type of the function. Metadata which does not follow
the conventions gives no information: None or empty defaultdicts. For a SERIES or SINGLETSFRAME,
the single metric is the one named by dataset_metadata.single_metric, otherwise the only one.

Fields of the functions taking one can be dotted paths, e.g. "inherited.site".
"""

import datetime
from collections import defaultdict
from collections.abc import Callable
from typing import Any

import pandas as pd

from hdhelpers.metadata._reading import (
    DISPLAY_NAME_FIELDS,
    SHORT_DISPLAY_NAME_FIELDS,
    Recording,
    dataset_default_timezone,
    dataset_recording,
)
from hdhelpers.metadata.attached import META_KEY, AnyMetadata, infer_data_type, read_metadata
from hdhelpers.metadata.conventions import TimeseriesDataType, _TimeseriesMetadataBase

_DEFAULT_AGGREGATION_METHOD = "MEAN"


def check_dataframe(data: pd.DataFrame) -> None:
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Input is not a pd.DataFrame")


def check_series(series: pd.Series) -> None:
    if not isinstance(series, pd.Series):
        raise TypeError("Input is not a pd.Series.")


def check_series_or_dataframe(data: pd.Series | pd.DataFrame) -> None:
    if not isinstance(data, pd.Series) and not isinstance(data, pd.DataFrame):
        raise TypeError("Input is not a pd.Series or pd.DataFrame.")


def _metadata(data: pd.Series | pd.DataFrame, data_type: TimeseriesDataType) -> AnyMetadata | None:
    """The attached metadata of any data type, otherwise the attrs parsed as data_type"""
    attached = data.attrs.get(META_KEY)
    if isinstance(attached, _TimeseriesMetadataBase):
        return attached  # type: ignore[return-value]
    return read_metadata(data, data_type)


def _single_metric(meta: AnyMetadata | None) -> str | None:
    """The single metric: dataset_metadata.single_metric if described, otherwise the only one"""
    if meta is None:
        return None
    metric_ids = meta.metric_ids()
    single_metric = meta.dataset_metadata.single_metric
    if single_metric is not None:
        return single_metric if single_metric in metric_ids else None
    return metric_ids[0] if len(metric_ids) == 1 else None


def _by_metric_by_column(
    data: pd.DataFrame, fields: str | tuple[str, ...], include_inherited: bool
) -> defaultdict[str, defaultdict[str, Any]]:
    check_dataframe(data)
    meta = _metadata(data, "MULTITSFRAME")
    infos = (
        {}
        if meta is None
        else meta.value_dimension_infos(fields, include_inherited=include_inherited)
    )
    return defaultdict(
        lambda: defaultdict(lambda: None),
        {metric: defaultdict(lambda: None, info) for metric, info in infos.items()},
    )


def _single_metric_by_column(
    data: pd.DataFrame, fields: str | tuple[str, ...], include_inherited: bool
) -> defaultdict[str, Any]:
    check_dataframe(data)
    meta = _metadata(data, "SINGLETSFRAME")
    metric = _single_metric(meta)
    if meta is None or metric is None:
        return defaultdict(lambda: None)
    return defaultdict(
        lambda: None,
        meta.value_dimension_infos(fields, include_inherited=include_inherited)[metric],
    )


def _series_value(series: pd.Series, fields: str | tuple[str, ...], include_inherited: bool) -> Any:
    check_series(series)
    meta = _metadata(series, "SERIES")
    metric = _single_metric(meta)
    if meta is None or metric is None:
        return None
    return meta.value_dimension_info(fields, metric, "value", include_inherited=include_inherited)


def _single_metric_or_dataset(
    data: pd.Series | pd.DataFrame,
    data_type: TimeseriesDataType,
    of_metric: Callable[[AnyMetadata, str], Any],
    of_dataset: Callable[[AnyMetadata], Any],
    empty: Any,
) -> Any:
    """Information of the single metric, of the dataset metadata if the metric is not found"""
    meta = _metadata(data, data_type)
    if meta is None:
        return empty
    metric = _single_metric(meta)
    return of_dataset(meta) if metric is None else of_metric(meta, metric)


# value dimensions of MULTITSFRAMEs


def get_units(
    multitsframe: pd.DataFrame, *, include_inherited: bool = False
) -> defaultdict[str, defaultdict[str, str | None]]:
    """Read units for each metric and value column.

    Args:
        multitsframe: DataFrame with per-metric metadata in attrs.
        include_inherited: Use inherited fields last, only for the "value" column.

    Returns:
        defaultdict[str, defaultdict[str, str | None]]:
            Units as result[metric_id][column]; unavailable units are None.

    Code example:

    .. doctest:: metadata.get_units

        >>> from hdhelpers.metadata.conventions import MULTITSFRAME_METADATA_EXAMPLE
        >>> multitsframe.attrs = MULTITSFRAME_METADATA_EXAMPLE
        >>> units = md.get_units(multitsframe)
        >>> units["plant_a.temperature"]["value"]
        '°C'
        >>> units["unknown metric"]["value"] is None
        True

    See :ref:`metadata-getter-values` for shared examples and return shapes.
    """  # noqa: E501
    return _by_metric_by_column(multitsframe, "unit", include_inherited)


def get_names(
    multitsframe: pd.DataFrame, *, include_inherited: bool = False
) -> defaultdict[str, defaultdict[str, str | None]]:
    """Read metadata names for each metric and value column.

    For the "value" column, try the metric's name after the column's own name.

    Args:
        multitsframe: DataFrame with per-metric metadata in attrs.
        include_inherited: Use inherited fields last, only for the "value" column.

    Returns:
        defaultdict[str, defaultdict[str, str | None]]:
            Names as result[metric_id][column]; unavailable names are None.

    Code example:

    .. doctest:: metadata.get_names

        >>> from hdhelpers.metadata.conventions import MULTITSFRAME_METADATA_EXAMPLE
        >>> multitsframe.attrs = MULTITSFRAME_METADATA_EXAMPLE
        >>> md.get_names(multitsframe)["plant_a.pressure"]["value"]
        'Plant A pressure'

    See :ref:`metadata-getter-names` for shared examples and return shapes.
    """
    return _by_metric_by_column(multitsframe, "name", include_inherited)


def get_display_names(
    multitsframe: pd.DataFrame, *, include_inherited: bool = False
) -> defaultdict[str, defaultdict[str, str | None]]:
    """Read display labels for each metric and value column.

    Use display_name, then name.

    Args:
        multitsframe: DataFrame with per-metric metadata in attrs.
        include_inherited: Use inherited fields last, only for the "value" column.

    Returns:
        defaultdict[str, defaultdict[str, str | None]]:
            Labels as result[metric_id][column]; unavailable labels are None.

    See :ref:`metadata-getter-names` for shared examples and return shapes.
    """
    return _by_metric_by_column(multitsframe, DISPLAY_NAME_FIELDS, include_inherited)


def get_short_display_names(
    multitsframe: pd.DataFrame, *, include_inherited: bool = False
) -> defaultdict[str, defaultdict[str, str | None]]:
    """Read short display labels for each metric and value column.

    Use short_display_name, then display_name, then name.

    Args:
        multitsframe: DataFrame with per-metric metadata in attrs.
        include_inherited: Use inherited fields last, only for the "value" column.

    Returns:
        defaultdict[str, defaultdict[str, str | None]]:
            Labels as result[metric_id][column]; unavailable labels are None.

    See :ref:`metadata-getter-names` for shared examples and return shapes.
    """
    return _by_metric_by_column(multitsframe, SHORT_DISPLAY_NAME_FIELDS, include_inherited)


def get_measurements(
    multitsframe: pd.DataFrame, *, include_inherited: bool = False
) -> defaultdict[str, defaultdict[str, str | None]]:
    """Read physical quantities for each metric and value column.

    For example, "temperature" is a measurement and "°C" is its unit.

    Args:
        multitsframe: DataFrame with per-metric metadata in attrs.
        include_inherited: Use inherited fields last, only for the "value" column.

    Returns:
        defaultdict[str, defaultdict[str, str | None]]:
            Quantities as result[metric_id][column]; unavailable quantities are None.

    See :ref:`metadata-getter-values` for shared examples and return shapes.
    """
    return _by_metric_by_column(multitsframe, "measurement", include_inherited)


def get_metric_info(
    multitsframe: pd.DataFrame, metric_info: str, *, include_inherited: bool = True
) -> defaultdict[str, Any]:
    """Read a metadata field for each metric.

    Search the metric, its "value" column, shared "value" metadata, then inherited fields
    (if enabled).

    Args:
        multitsframe: DataFrame with per-metric metadata in attrs.
        metric_info: Field name or dotted path, e.g. "sensor.model".
        include_inherited: Use inherited fields as a last fallback.

    Returns:
        defaultdict[str, Any]: Field values by metric ID; unresolved fields are None.

    Code example:

    .. doctest:: metadata.get_metric_info

        >>> from hdhelpers.metadata.conventions import MULTITSFRAME_METADATA_EXAMPLE
        >>> multitsframe.attrs = MULTITSFRAME_METADATA_EXAMPLE
        >>> md.get_metric_info(multitsframe, "recording_mode")["plant_a.temperature"]
        'on_change'

    See :ref:`metadata-getter-fields` for shared examples and return shapes.
    """
    check_dataframe(multitsframe)
    meta = _metadata(multitsframe, "MULTITSFRAME")
    infos = (
        {} if meta is None else meta.metric_infos(metric_info, include_inherited=include_inherited)
    )
    return defaultdict(lambda: None, infos)


# the value dimension "value" of SERIES


def get_series_info(
    series: pd.Series, value_dim_info: str, *, include_inherited: bool = True
) -> Any:
    """Read a metadata field for this Series.

    Search the "value" column, the metric, shared "value" metadata, then inherited fields
    (if enabled).

    Args:
        series: Series with metadata in attrs.
        value_dim_info: Field name or dotted path, e.g. "sensor.model".
        include_inherited: Use inherited fields as a last fallback.

    Returns:
        Any: Field value, or None when unavailable.

    Code example:

    .. doctest:: metadata.get_series_info

        >>> from hdhelpers.metadata.conventions import SERIES_METADATA_EXAMPLE
        >>> series.attrs = SERIES_METADATA_EXAMPLE
        >>> md.get_series_info(series, "decimals")
        2

    See :ref:`metadata-getter-fields` for shared examples and return shapes.
    """
    return _series_value(series, value_dim_info, include_inherited)


def get_series_unit(series: pd.Series, *, include_inherited: bool = False) -> str | None:
    """Read this Series' unit from metadata.

    Args:
        series: Series with metadata in attrs.
        include_inherited: Use inherited fields as a last fallback.

    Returns:
        str | None: Unit string; "" means dimensionless and None means unavailable.

    Code example:

    .. doctest:: metadata.get_series_unit

        >>> from hdhelpers.metadata.conventions import SERIES_METADATA_EXAMPLE
        >>> series.attrs = SERIES_METADATA_EXAMPLE
        >>> md.get_series_unit(series)
        'm'

    See :ref:`metadata-getter-values` for shared examples and return shapes.
    """
    return _series_value(series, "unit", include_inherited)  # type: ignore[no-any-return]


def get_series_name(series: pd.Series, *, include_inherited: bool = False) -> str | None:
    """Read this Series' name from metadata.

    Try the "value" column's name, then the metric's name.

    Args:
        series: Series with metadata in attrs.
        include_inherited: Use inherited fields as a last fallback.

    Returns:
        str | None: Resolved name, or None when unavailable.

    Code example:

    .. doctest:: metadata.get_series_name

        >>> from hdhelpers.metadata.conventions import SERIES_METADATA_EXAMPLE
        >>> series.attrs = SERIES_METADATA_EXAMPLE
        >>> md.get_series_name(series)
        'Water level north'

    See :ref:`metadata-getter-names` for shared examples and return shapes.
    """
    return _series_value(series, "name", include_inherited)  # type: ignore[no-any-return]


def get_series_display_name(series: pd.Series, *, include_inherited: bool = False) -> str | None:
    """Read the display label for this Series.

    Use display_name, then name.

    Args:
        series: Series with metadata in attrs.
        include_inherited: Use inherited fields as a last fallback.

    Returns:
        str | None: Resolved label, or None when unavailable.

    See :ref:`metadata-getter-names` for shared examples and return shapes.
    """
    return _series_value(  # type: ignore[no-any-return]
        series, DISPLAY_NAME_FIELDS, include_inherited
    )


def get_series_short_display_name(
    series: pd.Series, *, include_inherited: bool = False
) -> str | None:
    """Read the short display label for this Series.

    Use short_display_name, then display_name, then name.

    Args:
        series: Series with metadata in attrs.
        include_inherited: Use inherited fields as a last fallback.

    Returns:
        str | None: Resolved label, or None when unavailable.

    See :ref:`metadata-getter-names` for shared examples and return shapes.
    """
    return _series_value(  # type: ignore[no-any-return]
        series, SHORT_DISPLAY_NAME_FIELDS, include_inherited
    )


def get_series_measurement(series: pd.Series, *, include_inherited: bool = False) -> str | None:
    """Read this Series' physical quantity from metadata.

    For example, "temperature" describes the quantity and "°C" describes its unit.

    Args:
        series: Series with metadata in attrs.
        include_inherited: Use inherited fields as a last fallback.

    Returns:
        str | None: Quantity name, or None when unavailable.

    See :ref:`metadata-getter-values` for shared examples and return shapes.
    """
    return _series_value(series, "measurement", include_inherited)  # type: ignore[no-any-return]


# value dimensions of SINGLETSFRAMEs


def get_singlets_info(
    singletsframe: pd.DataFrame, value_dim_info: str, *, include_inherited: bool = True
) -> defaultdict[str, Any]:
    """Read a metadata field for each value column of a single-metric frame.

    For "value", search column, metric, shared and inherited metadata (if enabled), in that
    order. Other columns use their own and shared metadata.

    Args:
        singletsframe: DataFrame with one metric's metadata in attrs.
        value_dim_info: Field name or dotted path, e.g. "sensor.model".
        include_inherited: Use inherited fields last, only for the "value" column.

    Returns:
        defaultdict[str, Any]: Field values as result[column]; unresolved fields are None.

    Code example:

    .. doctest:: metadata.get_singlets_info

        >>> from hdhelpers.metadata.conventions import SINGLETSFRAME_METADATA_EXAMPLE
        >>> dataframe.attrs = SINGLETSFRAME_METADATA_EXAMPLE
        >>> md.get_singlets_info(dataframe, "name")["state"]
        'measurement state'

    See :ref:`metadata-getter-fields` for shared examples and return shapes.
    """
    return _single_metric_by_column(singletsframe, value_dim_info, include_inherited)


def get_singlets_units(
    singletsframe: pd.DataFrame, *, include_inherited: bool = False
) -> defaultdict[str, str | None]:
    """Read units for each value column of a single-metric frame.

    Args:
        singletsframe: DataFrame with one metric's metadata in attrs.
        include_inherited: Use inherited fields last, only for the "value" column.

    Returns:
        defaultdict[str, str | None]:
            Units as result[column]; "" means dimensionless and None means unavailable.

    Code example:

    .. doctest:: metadata.get_singlets_units

        >>> from hdhelpers.metadata.conventions import SINGLETSFRAME_METADATA_EXAMPLE
        >>> dataframe.attrs = SINGLETSFRAME_METADATA_EXAMPLE
        >>> md.get_singlets_units(dataframe)["value"]
        '°C'

    See :ref:`metadata-getter-values` for shared examples and return shapes.
    """
    return _single_metric_by_column(singletsframe, "unit", include_inherited)


def get_singlets_names(
    singletsframe: pd.DataFrame, *, include_inherited: bool = False
) -> defaultdict[str, str | None]:
    """Read metadata names for each value column of a single-metric frame.

    For "value", try the metric's name after the column's own name.

    Args:
        singletsframe: DataFrame with one metric's metadata in attrs.
        include_inherited: Use inherited fields last, only for the "value" column.

    Returns:
        defaultdict[str, str | None]: Names as result[column]; unavailable names are None.

    See :ref:`metadata-getter-names` for shared examples and return shapes.
    """
    return _single_metric_by_column(singletsframe, "name", include_inherited)


def get_singlets_display_names(
    singletsframe: pd.DataFrame, *, include_inherited: bool = False
) -> defaultdict[str, str | None]:
    """Read display labels for each value column of a single-metric frame.

    Use display_name, then name.

    Args:
        singletsframe: DataFrame with one metric's metadata in attrs.
        include_inherited: Use inherited fields last, only for the "value" column.

    Returns:
        defaultdict[str, str | None]: Labels as result[column]; unavailable labels are None.

    See :ref:`metadata-getter-names` for shared examples and return shapes.
    """
    return _single_metric_by_column(singletsframe, DISPLAY_NAME_FIELDS, include_inherited)


def get_singlets_short_display_names(
    singletsframe: pd.DataFrame, *, include_inherited: bool = False
) -> defaultdict[str, str | None]:
    """Read short display labels for each value column of a single-metric frame.

    Use short_display_name, then display_name, then name.

    Args:
        singletsframe: DataFrame with one metric's metadata in attrs.
        include_inherited: Use inherited fields last, only for the "value" column.

    Returns:
        defaultdict[str, str | None]: Labels as result[column]; unavailable labels are None.

    See :ref:`metadata-getter-names` for shared examples and return shapes.
    """
    return _single_metric_by_column(singletsframe, SHORT_DISPLAY_NAME_FIELDS, include_inherited)


def get_singlets_measurements(
    singletsframe: pd.DataFrame, *, include_inherited: bool = False
) -> defaultdict[str, str | None]:
    """Read physical quantities for each value column of a single-metric frame.

    For example, "temperature" is a measurement and "°C" is its unit.

    Args:
        singletsframe: DataFrame with one metric's metadata in attrs.
        include_inherited: Use inherited fields last, only for the "value" column.

    Returns:
        defaultdict[str, str | None]:
            Quantities as result[column]; unavailable quantities are None.

    See :ref:`metadata-getter-values` for shared examples and return shapes.
    """
    return _single_metric_by_column(singletsframe, "measurement", include_inherited)


def get_singlets_metric_info(
    singletsframe: pd.DataFrame, metric_info: str, *, include_inherited: bool = True
) -> Any:
    """Read one metadata field for the frame's single metric.

    Search the metric, its "value" column, shared "value" metadata, then inherited fields
    (if enabled).

    Args:
        singletsframe: DataFrame with one metric's metadata in attrs.
        metric_info: Field name or dotted path, e.g. "sensor.model".
        include_inherited: Use inherited fields as a last fallback.

    Returns:
        Any: One field value, or None when unavailable.

    Code example:

    Using :ref:`metadata-example-data`, compare a field of the metric with fields of its value
    dimensions. See :ref:`metadata-getter-fields` for the related getters:

    .. doctest:: metadata.get_singlets_metric_info

        >>> md.get_singlets_metric_info(dataframe, "name")
        'ABC temperature'
        >>> md.get_singlets_info(dataframe, "name")["state"]
        'measurement state'
    """
    check_dataframe(singletsframe)
    return _single_metric_or_dataset(
        singletsframe,
        "SINGLETSFRAME",
        lambda meta, metric: meta.metric_info(
            metric_info, metric, include_inherited=include_inherited
        ),
        lambda _meta: None,
        empty=None,
    )


# queried interval, time zones, recording and aggregation


def get_queried_interval(
    data: pd.Series | pd.DataFrame,
) -> tuple[datetime.datetime | None, datetime.datetime | None]:
    """Read the requested UTC time interval from dataset metadata.

    Args:
        data: Series or DataFrame with dataset metadata in attrs.

    Returns:
        tuple[datetime.datetime | None, datetime.datetime | None]:
            (start, end) as timezone-aware datetimes, or (None, None) if unavailable.

    Code example:

    .. doctest:: metadata.get_queried_interval

        >>> from hdhelpers.metadata.conventions import SERIES_METADATA_EXAMPLE
        >>> series.attrs = SERIES_METADATA_EXAMPLE
        >>> start, end = md.get_queried_interval(series)
        >>> start.isoformat()
        '2026-01-01T00:00:00+00:00'

    See :ref:`metadata-getter-values` for shared examples and return shapes.
    """
    check_series_or_dataframe(data)
    meta = _metadata(data, infer_data_type(data))
    return (None, None) if meta is None else meta.queried_interval()


def get_default_timezones(multitsframe: pd.DataFrame) -> defaultdict[str, str | None]:
    """Read the time zone recommended for calculations on each metric.

    Use the metric's default_timezone, then the dataset's default_timezone.

    Args:
        multitsframe: DataFrame with per-metric metadata in attrs.

    Returns:
        defaultdict[str, str | None]:
            Zone names or UTC offsets by metric ID, or None for unresolved zones. Missing
            IDs use the dataset default.

    Code example:

    .. doctest:: metadata.get_default_timezones

        >>> from hdhelpers.metadata.conventions import MULTITSFRAME_METADATA_EXAMPLE
        >>> multitsframe.attrs = MULTITSFRAME_METADATA_EXAMPLE
        >>> md.get_default_timezones(multitsframe)["plant_a.pressure"]
        'Europe/Berlin'

    See :ref:`metadata-getter-timezones` for shared examples and return shapes.
    """
    check_dataframe(multitsframe)
    meta = _metadata(multitsframe, "MULTITSFRAME")
    if meta is None:
        return defaultdict(lambda: None)
    dataset_timezone = dataset_default_timezone(meta)
    return defaultdict(lambda: dataset_timezone, meta.default_timezones())


def get_series_default_timezone(series: pd.Series) -> str | None:
    """Read the time zone recommended for calculations on this Series.

    Use the metric's default_timezone, then the dataset's default_timezone.

    Args:
        series: Series with metadata in attrs.

    Returns:
        str | None: Zone name or UTC offset, or None when neither source provides one.

    See :ref:`metadata-getter-timezones` for shared examples and return shapes.
    """
    check_series(series)
    return _single_metric_or_dataset(  # type: ignore[no-any-return]
        series,
        "SERIES",
        lambda meta, metric: meta.default_timezone(metric),
        dataset_default_timezone,
        empty=None,
    )


def get_singlets_default_timezone(singletsframe: pd.DataFrame) -> str | None:
    """Read the time zone recommended for calculations on a single-metric frame.

    Use the metric's default_timezone, then the dataset's default_timezone.

    Args:
        singletsframe: DataFrame with one metric's metadata in attrs.

    Returns:
        str | None: Zone name or UTC offset, or None when neither source provides one.

    See :ref:`metadata-getter-timezones` for shared examples and return shapes.
    """
    check_dataframe(singletsframe)
    return _single_metric_or_dataset(  # type: ignore[no-any-return]
        singletsframe,
        "SINGLETSFRAME",
        lambda meta, metric: meta.default_timezone(metric),
        dataset_default_timezone,
        empty=None,
    )


def get_recordings(multitsframe: pd.DataFrame) -> defaultdict[str, Recording]:
    """Read recording settings for each metric.

    Use the metric's frequency, offset and time zone together. If its frequency is missing,
    use the dataset's three fields instead.

    Args:
        multitsframe: DataFrame with per-metric metadata in attrs.

    Returns:
        defaultdict[str, Recording]:
            Settings by metric ID; missing IDs use dataset frequency settings.

    Code example:

    .. doctest:: metadata.get_recordings

        >>> from hdhelpers.metadata.conventions import MULTITSFRAME_METADATA_EXAMPLE
        >>> multitsframe.attrs = MULTITSFRAME_METADATA_EXAMPLE
        >>> md.get_recordings(multitsframe)["plant_a.temperature"].recording_mode
        'on_change'

    See :ref:`metadata-getter-recordings` for shared examples and return shapes.
    """
    check_dataframe(multitsframe)
    meta = _metadata(multitsframe, "MULTITSFRAME")
    if meta is None:
        return defaultdict(Recording)
    no_metadata = dataset_recording(meta)
    return defaultdict(lambda: no_metadata, meta.recordings())


def get_series_recording(series: pd.Series) -> Recording:
    """Read recording settings for this Series.

    Use the metric's frequency, offset and time zone together. If its frequency is missing,
    use the dataset's three fields instead.

    Args:
        series: Series with metadata in attrs.

    Returns:
        Recording: Recording object; absent metadata yields its default field values.

    See :ref:`metadata-getter-recordings` for shared examples and return shapes.
    """
    check_series(series)
    return _single_metric_or_dataset(  # type: ignore[no-any-return]
        series,
        "SERIES",
        lambda meta, metric: meta.recording(metric),
        dataset_recording,
        empty=Recording(),
    )


def get_singlets_recording(singletsframe: pd.DataFrame) -> Recording:
    """Read recording settings for a single-metric frame.

    Use the metric's frequency, offset and time zone together. If its frequency is missing,
    use the dataset's three fields instead.

    Args:
        singletsframe: DataFrame with one metric's metadata in attrs.

    Returns:
        Recording: Recording object; absent metadata yields its default field values.

    See :ref:`metadata-getter-recordings` for shared examples and return shapes.
    """
    check_dataframe(singletsframe)
    return _single_metric_or_dataset(  # type: ignore[no-any-return]
        singletsframe,
        "SINGLETSFRAME",
        lambda meta, metric: meta.recording(metric),
        dataset_recording,
        empty=Recording(),
    )


def get_default_aggregation_methods(multitsframe: pd.DataFrame) -> defaultdict[str, str]:
    """Read the default aggregation method for each metric.

    Use explicit default_aggregation_method (AVG becomes MEAN). Otherwise, metadata
    value_data_type selects LAST for boolean/string and MEAN for other types.

    Args:
        multitsframe: DataFrame with per-metric metadata in attrs.

    Returns:
        defaultdict[str, str]: Method names by metric ID; missing IDs default to MEAN.

    Code example:

    .. doctest:: metadata.get_default_aggregation_methods

        >>> from hdhelpers.metadata.conventions import MULTITSFRAME_METADATA_EXAMPLE
        >>> multitsframe.attrs = MULTITSFRAME_METADATA_EXAMPLE
        >>> methods = md.get_default_aggregation_methods(multitsframe)
        >>> methods["plant_a.temperature"], methods["plant_a.pressure"]
        ('MAX', 'MEAN')

    See :ref:`metadata-getter-aggregation` for shared examples and return shapes.
    """
    check_dataframe(multitsframe)
    meta = _metadata(multitsframe, "MULTITSFRAME")
    methods = {} if meta is None else meta.default_aggregation_methods()
    return defaultdict(lambda: _DEFAULT_AGGREGATION_METHOD, methods)


def get_series_default_aggregation_method(series: pd.Series) -> str:
    """Read the default aggregation method for this Series.

    Use explicit default_aggregation_method (AVG becomes MEAN). Otherwise, metadata
    value_data_type selects LAST for boolean/string and MEAN for other types.

    Args:
        series: Series with metadata in attrs.

    Returns:
        str: Method name; MEAN if metadata is unavailable.

    See :ref:`metadata-getter-aggregation` for shared examples and return shapes.
    """
    check_series(series)
    return _single_metric_or_dataset(  # type: ignore[no-any-return]
        series,
        "SERIES",
        lambda meta, metric: meta.default_aggregation_method(metric),
        lambda _meta: _DEFAULT_AGGREGATION_METHOD,
        empty=_DEFAULT_AGGREGATION_METHOD,
    )


def get_singlets_default_aggregation_method(singletsframe: pd.DataFrame) -> str:
    """Read the default aggregation method for a single-metric frame.

    Use explicit default_aggregation_method (AVG becomes MEAN). Otherwise, metadata
    value_data_type selects LAST for boolean/string and MEAN for other types.

    Args:
        singletsframe: DataFrame with one metric's metadata in attrs.

    Returns:
        str: Method name; MEAN if metadata is unavailable.

    See :ref:`metadata-getter-aggregation` for shared examples and return shapes.
    """
    check_dataframe(singletsframe)
    return _single_metric_or_dataset(  # type: ignore[no-any-return]
        singletsframe,
        "SINGLETSFRAME",
        lambda meta, metric: meta.default_aggregation_method(metric),
        lambda _meta: _DEFAULT_AGGREGATION_METHOD,
        empty=_DEFAULT_AGGREGATION_METHOD,
    )


def copy_without_metadata[T: (pd.Series, pd.DataFrame)](data: T) -> T:
    """Copy a Series or DataFrame with all attrs removed.

    Data is shared until either object is modified (pandas copy on write).

    Args:
        data (pd.Series | pd.DataFrame): Source object; left unchanged.

    Returns:
        pd.Series | pd.DataFrame: Copy with empty attrs.

    Code example:

    .. doctest:: metadata.copy_without_metadata

        >>> multitsframe.attrs = {"dataset_metadata": {"metric_key": "id"}, "metrics": []}
        >>> data = md.copy_without_metadata(multitsframe)
        >>> data.attrs
        {}
        >>> multitsframe.attrs
        {'dataset_metadata': {'metric_key': 'id'}, 'metrics': []}
    """
    check_series_or_dataframe(data)
    # The constructor does not copy attrs, in contrast to e.g. copy(deep=False)
    copy = type(data)(data)
    copy.attrs = {}
    return copy
