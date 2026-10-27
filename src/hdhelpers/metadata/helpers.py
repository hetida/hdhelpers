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
    """Units of the value dimensions of the metrics of a MULTITSFRAME

    The value dimensions of a metric are its own ones, "value" and the shared ones
    (value_dimensions_shared).

    Args:
        multitsframe (pd.DataFrame): MULTITSFRAME with metadata following the conventions.
        include_inherited (bool): Whether the properties a metric inherits from objects higher up in an asset hierarchy ("inherited") are the last resort for the value dimension "value". Defaults to False, since this information should be provided for the metric itself.

    Returns:
        defaultdict[str, defaultdict[str, str | None]]: The unit by column by metric, None if unknown.

    Code example:

    .. doctest:: metadata.get_units

        >>> from hdhelpers.metadata.conventions import MULTITSFRAME_METADATA_EXAMPLE
        >>> multitsframe.attrs = MULTITSFRAME_METADATA_EXAMPLE
        >>> units = get_units(multitsframe)
        >>> units["plant_a.temperature"]["value"]
        '°C'
        >>> units["unknown metric"]["value"] is None
        True
    """  # noqa: E501
    return _by_metric_by_column(multitsframe, "unit", include_inherited)


def get_names(
    multitsframe: pd.DataFrame, *, include_inherited: bool = False
) -> defaultdict[str, defaultdict[str, str | None]]:
    """Names of the value dimensions of the metrics of a MULTITSFRAME, see get_units

    The name of the value dimension "value" falls back to the name of the metric.

    Code example:

    .. doctest:: metadata.get_names

        >>> from hdhelpers.metadata.conventions import MULTITSFRAME_METADATA_EXAMPLE
        >>> multitsframe.attrs = MULTITSFRAME_METADATA_EXAMPLE
        >>> get_names(multitsframe)["plant_a.pressure"]["value"]
        'Plant A pressure'
    """
    return _by_metric_by_column(multitsframe, "name", include_inherited)


def get_display_names(
    multitsframe: pd.DataFrame, *, include_inherited: bool = False
) -> defaultdict[str, defaultdict[str, str | None]]:
    """Display names of the value dimensions of the metrics of a MULTITSFRAME, see get_units

    Fall back to the names.
    """
    return _by_metric_by_column(multitsframe, DISPLAY_NAME_FIELDS, include_inherited)


def get_short_display_names(
    multitsframe: pd.DataFrame, *, include_inherited: bool = False
) -> defaultdict[str, defaultdict[str, str | None]]:
    """Short display names of the value dimensions of the metrics of a MULTITSFRAME

    Fall back to the display names and the names, see get_units.
    """
    return _by_metric_by_column(multitsframe, SHORT_DISPLAY_NAME_FIELDS, include_inherited)


def get_measurements(
    multitsframe: pd.DataFrame, *, include_inherited: bool = False
) -> defaultdict[str, defaultdict[str, str | None]]:
    """Measured quantities of the value dimensions of the metrics of a MULTITSFRAME

    See get_units.
    """
    return _by_metric_by_column(multitsframe, "measurement", include_inherited)


def get_metric_info(
    multitsframe: pd.DataFrame, metric_info: str, *, include_inherited: bool = True
) -> defaultdict[str, Any]:
    """A field of the metrics of a MULTITSFRAME by metric

    The field of the metric itself, otherwise of its value dimension "value", of the shared value
    dimension "value" and, if include_inherited, of the properties the metric inherits.

    Args:
        multitsframe (pd.DataFrame): MULTITSFRAME with metadata following the conventions.
        metric_info (str): Field or dotted path of fields, e.g. "inherited.site".
        include_inherited (bool): Whether to fall back to the inherited properties.

    Returns:
        defaultdict[str, Any]: The information by metric, None if unknown.

    Code example:

    .. doctest:: metadata.get_metric_info

        >>> from hdhelpers.metadata.conventions import MULTITSFRAME_METADATA_EXAMPLE
        >>> multitsframe.attrs = MULTITSFRAME_METADATA_EXAMPLE
        >>> get_metric_info(multitsframe, "recording_mode")["plant_a.temperature"]
        'on_change'
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
    """A field of the value dimension "value" of the single metric of a SERIES

    Looked up on the value dimension, the metric, the shared value dimension and, if
    include_inherited, the properties the metric inherits.

    Code example:

    .. doctest:: metadata.get_series_info

        >>> from hdhelpers.metadata.conventions import SERIES_METADATA_EXAMPLE
        >>> series.attrs = SERIES_METADATA_EXAMPLE
        >>> get_series_info(series, "decimals")
        2
    """
    return _series_value(series, value_dim_info, include_inherited)


def get_series_unit(series: pd.Series, *, include_inherited: bool = False) -> str | None:
    """Unit of the values of a SERIES

    Code example:

    .. doctest:: metadata.get_series_unit

        >>> from hdhelpers.metadata.conventions import SERIES_METADATA_EXAMPLE
        >>> series.attrs = SERIES_METADATA_EXAMPLE
        >>> get_series_unit(series)
        'm'
    """
    return _series_value(series, "unit", include_inherited)  # type: ignore[no-any-return]


def get_series_name(series: pd.Series, *, include_inherited: bool = False) -> str | None:
    """Name of the values of a SERIES, falling back to the name of its metric

    Code example:

    .. doctest:: metadata.get_series_name

        >>> from hdhelpers.metadata.conventions import SERIES_METADATA_EXAMPLE
        >>> series.attrs = SERIES_METADATA_EXAMPLE
        >>> get_series_name(series)
        'Water level north'
    """
    return _series_value(series, "name", include_inherited)  # type: ignore[no-any-return]


def get_series_display_name(series: pd.Series, *, include_inherited: bool = False) -> str | None:
    """Display name of the values of a SERIES, falling back to the name"""
    return _series_value(  # type: ignore[no-any-return]
        series, DISPLAY_NAME_FIELDS, include_inherited
    )


def get_series_short_display_name(
    series: pd.Series, *, include_inherited: bool = False
) -> str | None:
    """Short display name of the values of a SERIES, falling back to display name and name"""
    return _series_value(  # type: ignore[no-any-return]
        series, SHORT_DISPLAY_NAME_FIELDS, include_inherited
    )


def get_series_measurement(series: pd.Series, *, include_inherited: bool = False) -> str | None:
    """Measured quantity of the values of a SERIES"""
    return _series_value(series, "measurement", include_inherited)  # type: ignore[no-any-return]


# value dimensions of SINGLETSFRAMEs


def get_singlets_info(
    singletsframe: pd.DataFrame, value_dim_info: str, *, include_inherited: bool = True
) -> defaultdict[str, Any]:
    """A field of the value dimensions of the single metric of a SINGLETSFRAME by column

    Code example:

    .. doctest:: metadata.get_singlets_info

        >>> from hdhelpers.metadata.conventions import SINGLETSFRAME_METADATA_EXAMPLE
        >>> dataframe.attrs = SINGLETSFRAME_METADATA_EXAMPLE
        >>> get_singlets_info(dataframe, "name")["state"]
        'measurement state'
    """
    return _single_metric_by_column(singletsframe, value_dim_info, include_inherited)


def get_singlets_units(
    singletsframe: pd.DataFrame, *, include_inherited: bool = False
) -> defaultdict[str, str | None]:
    """Units of the value dimensions of a SINGLETSFRAME by column

    Code example:

    .. doctest:: metadata.get_singlets_units

        >>> from hdhelpers.metadata.conventions import SINGLETSFRAME_METADATA_EXAMPLE
        >>> dataframe.attrs = SINGLETSFRAME_METADATA_EXAMPLE
        >>> get_singlets_units(dataframe)["value"]
        '°C'
    """
    return _single_metric_by_column(singletsframe, "unit", include_inherited)


def get_singlets_names(
    singletsframe: pd.DataFrame, *, include_inherited: bool = False
) -> defaultdict[str, str | None]:
    """Names of the value dimensions of a SINGLETSFRAME by column, see get_singlets_units"""
    return _single_metric_by_column(singletsframe, "name", include_inherited)


def get_singlets_display_names(
    singletsframe: pd.DataFrame, *, include_inherited: bool = False
) -> defaultdict[str, str | None]:
    """Display names of the value dimensions of a SINGLETSFRAME, falling back to the names"""
    return _single_metric_by_column(singletsframe, DISPLAY_NAME_FIELDS, include_inherited)


def get_singlets_short_display_names(
    singletsframe: pd.DataFrame, *, include_inherited: bool = False
) -> defaultdict[str, str | None]:
    """Short display names of the value dimensions of a SINGLETSFRAME, see get_singlets_units

    Fall back to the display names and the names.
    """
    return _single_metric_by_column(singletsframe, SHORT_DISPLAY_NAME_FIELDS, include_inherited)


def get_singlets_measurements(
    singletsframe: pd.DataFrame, *, include_inherited: bool = False
) -> defaultdict[str, str | None]:
    """Measured quantities of the value dimensions of a SINGLETSFRAME by column"""
    return _single_metric_by_column(singletsframe, "measurement", include_inherited)


def get_singlets_metric_info(
    singletsframe: pd.DataFrame, metric_info: str, *, include_inherited: bool = True
) -> Any:
    """A field of the single metric of a SINGLETSFRAME, see get_metric_info for the fallbacks"""
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
    """Start and end of the queried interval (the ref interval), None if unknown

    Code example:

    .. doctest:: metadata.get_queried_interval

        >>> from hdhelpers.metadata.conventions import SERIES_METADATA_EXAMPLE
        >>> series.attrs = SERIES_METADATA_EXAMPLE
        >>> start, end = get_queried_interval(series)
        >>> start.isoformat()
        '2026-01-01T00:00:00+00:00'
    """
    check_series_or_dataframe(data)
    meta = _metadata(data, infer_data_type(data))
    return (None, None) if meta is None else meta.queried_interval()


def get_default_timezones(multitsframe: pd.DataFrame) -> defaultdict[str, str | None]:
    """The default time zone of each metric of a MULTITSFRAME

    The one of the metric, otherwise the one of the dataset metadata, which is also the default
    of the returned defaultdict.

    Code example:

    .. doctest:: metadata.get_default_timezones

        >>> from hdhelpers.metadata.conventions import MULTITSFRAME_METADATA_EXAMPLE
        >>> multitsframe.attrs = MULTITSFRAME_METADATA_EXAMPLE
        >>> get_default_timezones(multitsframe)["plant_a.pressure"]
        'Europe/Berlin'
    """
    check_dataframe(multitsframe)
    meta = _metadata(multitsframe, "MULTITSFRAME")
    if meta is None:
        return defaultdict(lambda: None)
    dataset_timezone = dataset_default_timezone(meta)
    return defaultdict(lambda: dataset_timezone, meta.default_timezones())


def get_series_default_timezone(series: pd.Series) -> str | None:
    """The default time zone of the single metric of a SERIES, see get_default_timezones"""
    check_series(series)
    return _single_metric_or_dataset(  # type: ignore[no-any-return]
        series,
        "SERIES",
        lambda meta, metric: meta.default_timezone(metric),
        dataset_default_timezone,
        empty=None,
    )


def get_singlets_default_timezone(singletsframe: pd.DataFrame) -> str | None:
    """The default time zone of the single metric of a SINGLETSFRAME, see get_default_timezones"""
    check_dataframe(singletsframe)
    return _single_metric_or_dataset(  # type: ignore[no-any-return]
        singletsframe,
        "SINGLETSFRAME",
        lambda meta, metric: meta.default_timezone(metric),
        dataset_default_timezone,
        empty=None,
    )


def get_recordings(multitsframe: pd.DataFrame) -> defaultdict[str, Recording]:
    """How the values of each metric of a MULTITSFRAME are recorded

    The frequency, its offset and time zone fall back to the ones of the dataset metadata as a
    whole. The default of the returned defaultdict is the recording of a metric without
    metadata, i.e. with the frequency of the dataset metadata.

    Code example:

    .. doctest:: metadata.get_recordings

        >>> from hdhelpers.metadata.conventions import MULTITSFRAME_METADATA_EXAMPLE
        >>> multitsframe.attrs = MULTITSFRAME_METADATA_EXAMPLE
        >>> get_recordings(multitsframe)["plant_a.temperature"].recording_mode
        'on_change'
    """
    check_dataframe(multitsframe)
    meta = _metadata(multitsframe, "MULTITSFRAME")
    if meta is None:
        return defaultdict(Recording)
    no_metadata = dataset_recording(meta)
    return defaultdict(lambda: no_metadata, meta.recordings())


def get_series_recording(series: pd.Series) -> Recording:
    """How the values of a SERIES are recorded, see get_recordings"""
    check_series(series)
    return _single_metric_or_dataset(  # type: ignore[no-any-return]
        series,
        "SERIES",
        lambda meta, metric: meta.recording(metric),
        dataset_recording,
        empty=Recording(),
    )


def get_singlets_recording(singletsframe: pd.DataFrame) -> Recording:
    """How the values of a SINGLETSFRAME are recorded, see get_recordings"""
    check_dataframe(singletsframe)
    return _single_metric_or_dataset(  # type: ignore[no-any-return]
        singletsframe,
        "SINGLETSFRAME",
        lambda meta, metric: meta.recording(metric),
        dataset_recording,
        empty=Recording(),
    )


def get_default_aggregation_methods(multitsframe: pd.DataFrame) -> defaultdict[str, str]:
    """The default aggregation method of each metric of a MULTITSFRAME

    The method of the metric, with "AVG" as "MEAN". Otherwise "LAST" for boolean and string
    values and "MEAN" for all others, which is also the default of the returned defaultdict.

    Code example:

    .. doctest:: metadata.get_default_aggregation_methods

        >>> from hdhelpers.metadata.conventions import MULTITSFRAME_METADATA_EXAMPLE
        >>> multitsframe.attrs = MULTITSFRAME_METADATA_EXAMPLE
        >>> methods = get_default_aggregation_methods(multitsframe)
        >>> methods["plant_a.temperature"], methods["plant_a.pressure"]
        ('MAX', 'MEAN')
    """
    check_dataframe(multitsframe)
    meta = _metadata(multitsframe, "MULTITSFRAME")
    methods = {} if meta is None else meta.default_aggregation_methods()
    return defaultdict(lambda: _DEFAULT_AGGREGATION_METHOD, methods)


def get_series_default_aggregation_method(series: pd.Series) -> str:
    """The default aggregation method of a SERIES, see get_default_aggregation_methods"""
    check_series(series)
    return _single_metric_or_dataset(  # type: ignore[no-any-return]
        series,
        "SERIES",
        lambda meta, metric: meta.default_aggregation_method(metric),
        lambda _meta: _DEFAULT_AGGREGATION_METHOD,
        empty=_DEFAULT_AGGREGATION_METHOD,
    )


def get_singlets_default_aggregation_method(singletsframe: pd.DataFrame) -> str:
    """The default aggregation method of a SINGLETSFRAME, see get_default_aggregation_methods"""
    check_dataframe(singletsframe)
    return _single_metric_or_dataset(  # type: ignore[no-any-return]
        singletsframe,
        "SINGLETSFRAME",
        lambda meta, metric: meta.default_aggregation_method(metric),
        lambda _meta: _DEFAULT_AGGREGATION_METHOD,
        empty=_DEFAULT_AGGREGATION_METHOD,
    )


def copy_without_metadata[T: (pd.Series, pd.DataFrame)](data: T) -> T:
    """Gets a copy of a Series or DataFrame without its metadata

    The copy is cheap: It shares the data with ``data`` until one of them is changed (copy on
    write), so changing the copy does not change ``data``. pandas operations do not copy
    metadata attached as model (see attach_metadata), but they copy plain metadata in attrs
    deeply for every object they create.

    Args:
        data (pd.Series | pd.DataFrame): Series or DataFrame, e.g. a MTSF with metadata.

    Returns:
        pd.Series | pd.DataFrame: Copy of ``data`` with empty ``attrs``.

    Code example:

    .. doctest:: metadata.copy_without_metadata

        >>> multitsframe.attrs = {"dataset_metadata": {"metric_key": "id"}, "metrics": []}
        >>> data = copy_without_metadata(multitsframe)
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
