import logging
import datetime
from collections import defaultdict
from typing import Any

import pandas as pd


from hdhelpers.structure_metadata import MTSMetadata, SeriesMetadata
from hdhelpers.exceptions import HelperException

logger = logging.getLogger("hdhelpers")

def _check_series(timeseries_object: Any):
    if not isinstance(timeseries_object, pd.Series):
        raise TypeError("Please use pandas Series for this function.")

def _check_mts(timeseries_object: Any):
    if not isinstance(timeseries_object, pd.DataFrame):
        raise TypeError("Please use pandas Dataframe for this function.")
    if (timeseries_object.columns not in ["timestamp", "value", "metric"]).any():
        raise HelperException("Please use valid MTS.")

def _load_metadata_from_series(timeseries_object: pd.Series) -> SeriesMetadata:
    _check_series(timeseries_object)
    return SeriesMetadata(**timeseries_object.attrs) # type: ignore[misc]


def _load_metadata_from_mts(timeseries_object: pd.DataFrame) -> MTSMetadata:
    _check_mts(timeseries_object)
    return MTSMetadata(**timeseries_object.attrs) # type: ignore[misc]


def _load_metadata(timeseries_object: pd.DataFrame | pd.Series) -> MTSMetadata | SeriesMetadata:
    if isinstance(timeseries_object, pd.Series):
        return _load_metadata_from_series(timeseries_object)
    if isinstance(timeseries_object, pd.Series):
        return _load_metadata_from_mts(timeseries_object)
    raise TypeError("Please use pandas Series or Dataframe for loading metadata.")


## Metadata Dataset
def get_queried_interval(timeseries_object: pd.Series | pd.DataFrame) -> tuple[datetime.datetime|None, datetime.datetime|None]:
    """Get queried interval from metadata

    Args:
        timeseries_object (pd.Series | pd.DataFrame): Series or Dataframe with metadata following the convention

    Returns:
        tuple[datetime.datetime|None, datetime.datetime|None]: Tuple of available start and end date of requested interval.

    Raises:
        ValueError: If metadata of `timeseries_object` is not None and not convertable to a datetime-object (ISO-format is expected).
        TypeError: If `timeseries_object` is not a Series or Dataframe.

    Examples:
        >>> attr = {
        ...        "dataset_metadata": {
        ...        "ref_interval_start_timestamp": "2025-11-05T13:28:00Z",
        ...        "ref_interval_end_timestamp": "2025-11-06T13:28:00Z" }
        ...    }
        ...    series = pd.Series()
        ...    series.attrs = attr
        ...    get_queried_interval(series)
        datetime.datetime(2025,11,5,31,28, tzinfo=datetime.UTC), datetime.datetime(2025,11,6,31,28, tzinfo=datetime.UTC)
    """
    metadata = _load_metadata(timeseries_object)

    start = datetime.datetime.fromisoformat(metadata.get_start())  if metadata.get_start() else None
    end = datetime.datetime.fromisoformat(metadata.get_end())  if metadata.get_end() else None

    return start, end

## Series
def get_series_unit(timeseries_object: pd.Series) -> str | None:
    """Gets name of the series from metadata

    Args:
        timeseries_object (pd.Series): Series with metadata following the convention

    Returns:
        str | None:
            Returns the unit of the value.
            If the unit of the value is not present it returns None.

    Raises:
        TypeError: If `timeseries_object` is not a Series.

    Examples:
    >>> attr = { "by_metric": { "series": {"value_dimensions": {}}}}
    ...    series = pd.Series()
    ...    series.attrs = attr
    ...    get_series_unit(series)
    None
    >>> attr = { "by_metric": { "series": {"value_dimensions": {"value": {"unit":None}}}}}
    ...    series = pd.Series()
    ...    series.attrs = attr
    ...    get_series_unit(series)
    None
    >>> attr = { "by_metric": { "series": {"value_dimensions": {"value": {"unit":"m/s"}}}}}
    ...    series = pd.Series()
    ...    series.attrs = attr
    ...    get_series_unit(series)
    "m/s"
    """
    metadata = _load_metadata_from_series(timeseries_object)
    return metadata.get_unit()

def get_series_name(timeseries_object: pd.Series) -> str | None:
    """Gets name of the series from metadata

    Args:
        timeseries_object (pd.Series): Series with metadata following the convention

    Returns:
        str | None:
            Returns the name of the value.
            If the name of the value is not present it returns the name of the metric.
            If the metric name is not present it returns None.

    Raises:
        TypeError: If `timeseries_object` is not a Series.

    Examples:
    >>> attr = { "by_metric": { "series": {"value_dimensions": {"value": {"name": "value_name_of_series"}}}}}
    ...    series = pd.Series()
    ...    series.attrs = attr
    ...    get_series_name(series)
    "value_name_of_series"
    >>> attr = { "by_metric": { "series": {"metric": {"name": "name_of_series"}}}}
    ...    series = pd.Series()
    ...    series.attrs = attr
    ...    get_series_name(series)
    "name_of_series"
    >>> attr = { "by_metric": { "series": {"metric": {"name": "name_of_series"}},
    ...                                   "value_dimensions": {"value": {"name": "value_name_of_series"}}}}
    ...    series = pd.Series()
    ...    series.attrs = attr
    ...    get_series_name(series)
    "name_of_series"
    """
    metadata = _load_metadata_from_series(timeseries_object)
    return metadata.get_name()

def get_series_display_name(timeseries_object: pd.Series) -> str | None:
    """Gets display name of the series from metadata

    Args:
        timeseries_object (pd.Series): Series with metadata following the convention

    Returns:
        str | None:
            Returns the display name of the value.
            If the display name of the value is not present it returns the display name of the metric.
            If the metric display name is not present it returns the result of get_series_name().

    Raises:
        TypeError: If `timeseries_object` is not a Series.

    Examples:
    >>> attr = { "by_metric": { "series": {"metric": {"display_name": "display_name_of_series"}}}}
    ...    series = pd.Series()
    ...    series.attrs = attr
    ...    get_series_display_name(series)
    "display_name_of_series"
    """
    metadata = _load_metadata_from_series(timeseries_object)
    return metadata.get_display_name()


def get_series_short_display_name(timeseries_object: pd.Series) -> str | None:
    """Gets short display name of the Series from metadata

    Args:
        timeseries_object (pd.Series): Series with metadata following the convention

    Returns:
        str | None:
            Returns the short display name of the value.
            If the short display name of the value is not present it returns the short display name of the metric.
            If the metric short display name is not present it returns the result of series_display_name().

    Raises:
        TypeError: If `timeseries_object` is not a Series.

    Examples:
    >>> attr = { "by_metric": { "series": "metric": {"short_display_name": "short_display_name_of_series"}}}}
    ...    series = pd.Series()
    ...    series.attrs = attr
    ...    get_series_short_display_name(series)
    "short_display_name_of_series"
    """
    metadata = _load_metadata_from_series(timeseries_object)
    return metadata.get_short_display_name()


# MTS Metric
def get_metric_names(timeseries_object: pd.DataFrame) -> dict[str, str | None]:
    """Gets names of the MTS metrics from Metadata

    Args:
        timeseries_object (pd.DataFrame): MTS with metadata following the convention.

    Returns:
        dict[str, str | None]: Dictionary of metrics containing the names.
            If the name is not present for a metric the corresponding value is None.

    Raises:
        TypeError: If `timeseries_object` is not a DataFrame.

    Examples:
    >>> attr = { "by_metric": { "metric1": "metric": {"name": "name_of_metric1"}},
    ...                       { "metric2": "metric": {"name": "name_of_metric2"}}}
    ...    dataframe = pd.DataFrame()
    ...    dataframe.attrs = attr
    ...    get_metric_names(series)
    { "metric1": "name_of_metric1", "metric2": "name_of_metric2"}
    """
    return defaultdict(lambda: None)


def get_metric_display_names(timeseries_object: pd.DataFrame) -> dict[str, str | None]:
    """Gets display names of the MTS metrics from Metadata

    Args:
        timeseries_object (pd.DataFrame): MTS with metadata following the convention.

    Returns:
        dict[str, str | None]: Dictionary of metrics containing the display names.
        If the display name of the metrics is not present it returns the result of get_metric_names().

    Raises:
        TypeError: If `timeseries_object` is not a DataFrame.

    Examples:
    >>> attr = { "by_metric": { "metric1": "metric": {"display_name": "display_name_of_metric1"}},
    ...                       { "metric2": "metric": {"name": "name_of_metric2"}}}
    ...    dataframe = pd.DataFrame()
    ...    dataframe.attrs = attr
    ...    get_metric_names(dataframe)
    { "metric1": "display_name_of_metric1", "metric2": "name_of_metric2"}
    """
    return defaultdict(lambda: None)


def get_metric_short_display_names(timeseries_object: pd.DataFrame) -> dict[str, str | None]:
    """Gets short display names of the MTS metrics from Metadata

    Args:
        timeseries_object (pd.DataFrame): MTS with metadata following the convention.

    Returns:
        dict[str, str | None]: Dictionary of metrics containing the short display names.
        If the short display name of the metrics is not present it returns the result of get_metric_display_names().

    Raises:
        TypeError: If `timeseries_object` is not a DataFrame.

    Examples:
    >>> attr = { "by_metric": { "metric1": "metric": {"short_display_name": "short_display_name_of_metric1"}},
    ...                       { "metric2": "metric": {"name": "name_of_metric2"}},
    ...                       { "metric3" : {}} }
    ...    dataframe = pd.DataFrame()
    ...    dataframe.attrs = attr
    ...    get_metric_short_display_names(dataframe)
    { "metric1": "short_display_name_of_metric1", "metric2": "name_of_metric2", "metric3": None}
    """
    return defaultdict(lambda: None)


# MTS value_dimensions
def get_values_names(timeseries_object: pd.DataFrame) -> dict[str, dict[str, str | None] | None]:
    """Gets names of value dimensions in MTS metrics from Metadata

    Args:
        timeseries_object (pd.DataFrame): MTS with metadata following the convention.

    Returns:
        dict[str, dict[str | None] | None]: Dictionary of metrics containing the names of the value dimensions.
        If the name of the value_dimension is not present it returns the name of the metric.
        If the name of the metric is not present it returns None as value of the corresponding key.
        In case a metric does not have any information regarding a corresponding value_dimension an empty dict is returned

    Raises:
        TypeError: If `timeseries_object` is not a DataFrame.

    Examples:
    >>> attr = { "by_metric": { "metric1": "value_dimension": {"value_dim_1" : {"name": "name_of_value_dim1"}}},
    ...                       { "metric2": "metric": {"name": "name_of_metric2"}, "value_dim_1": {}},
    ...                       { "metric3" : "metric": {"name": "name_of_metric3"}},
    ...                       { "metric4" : "metric": {}, "value_dim_1": {}  }}
    ...    dataframe = pd.DataFrame()
    ...    dataframe.attrs = attr
    ...    get_values_names(dataframe)
    { "metric1": {"value_dim_1": "name_of_value_dim1"}, "metric2": {"value_dim_1": "name_of_metric2"}, "metric3: {}, "metric4": {"value_dim_1": None}}
    """
    return defaultdict(lambda: defaultdict(lambda: None))

def get_values_display_names(timeseries_object: pd.DataFrame) -> dict[str, dict[str, str | None] | None]:
    """Gets display names of value dimensions in MTS metrics from Metadata

    Args:
        timeseries_object (pd.DataFrame): MTS with metadata following the convention.

    Returns:
        dict[str, dict[str | None] | None]: Dictionary of metrics containing the names of the value dimensions.
        If the display name of the value_dimension is not present it returns the result of get_values_names().

    Raises:
        TypeError: If `timeseries_object` is not a DataFrame.

    Examples:
    >>> attr = { "by_metric": { "metric1": "value_dimension": {"value_dim_1" : {"display_name": "display_name_of_value_dim1"}}},
    ...                       { "metric2": "metric": {"name": "name_of_metric2"}, "value_dim_1": {"name": "name_of_value_dim_1"}},
    ...                       { "metric3" : "metric": {"name": "name_of_metric3"}}, "value_dim_1": {}}
    ...    dataframe = pd.DataFrame()
    ...    dataframe.attrs = attr
    ...    get_values_display_names(dataframe)
    { "metric1": {"value_dim_1": "display_name_of_value_dim1"}, "metric2": {"value_dim_1": "name_of_value_dim_1"}, "metric3: {"name_of_metric3"}}
    """
    return defaultdict(lambda: defaultdict(lambda: None))


def get_values_short_display_names(timeseries_object: pd.DataFrame) -> dict[str, dict[dict, str | None] | None]:
    """Gets short display names of value dimensions in MTS metrics from Metadata

    Args:
        timeseries_object (pd.DataFrame): MTS with metadata following the convention.

    Returns:
        dict[str, dict[str | None] | None]: Dictionary of metrics containing the names of the value dimensions.
        If the short display name of the value_dimension is not present it returns the result of get_values_display_names().

    Raises:
        TypeError: If `timeseries_object` is not a DataFrame.

    Examples:
    >>> attr = { "by_metric": { "metric1": "value_dimension": {"value_dim_1" : {"short_display_name": "short_display_name_of_value_dim1"}}},
    ...                       { "metric2": "metric": {"short_display_name": "name_of_metric2"}, "value_dim_1": {"name": "name_of_value_dim_1"}},
    ...                       { "metric3" : "metric": {"name": "name_of_metric3"}}, "value_dim_1": {}}
    ...    dataframe = pd.DataFrame()
    ...    dataframe.attrs = attr
    ...    get_values_short_display_names(dataframe)
    { "metric1": {"value_dim_1": "short_display_name_of_value_dim1"}, "metric2": {"value_dim_1": "name_of_value_dim_1"}, "metric3: {"value_dim_1": name_of_metric3}}
    """
    return defaultdict(lambda: defaultdict(lambda: None))

def get_units(timeseries_object: pd.DataFrame) -> dict[str, dict[str, str | None] | None]:
    """Gets unit of value dimensions in MTS metrics from Metadata

    Args:
        timeseries_object (pd.DataFrame): MTS with metadata following the convention.

    Returns:
        dict[str, dict[str | None] | None]: Dictionary of metrics containing the names of the value dimensions.
        If the short display name of the value_dimension is not present it returns the result of get_values_display_names().

    Raises:
        TypeError: If `timeseries_object` is not a DataFrame.

    Examples:
    >>> attr = { "by_metric": { "metric1": "value_dimension": {"value_dim_1" : {"unit": "m"}}},
    ...                       { "metric2": "value_dim_1": {"name": "name_of_value_dim_1"}},
    ...                       { "metric3" : "value_dim_1": {}, "value_dim_2": {"unit": "km"}}
    ...    dataframe = pd.DataFrame()
    ...    dataframe.attrs = attr
    ...    get_values_display_names(dataframe)
    { "metric1": {"value_dim_1": "m"}, "metric2": {"value_dim_1": None}, "metric3:  {"value_dim_1": None, "value_dim_2": "km"}}
    """
    return defaultdict(lambda: defaultdict(lambda: None))


# MTS only one value_dimension
def get_unit_by_metric(timeseries_object: pd.DataFrame) -> dict[str, str|None]:
    """Gets unit by metric if all metrics contain only one value_dimension

    Args:
        timeseries_object (pd.DataFrame): MTS with metadata following the convention.

    Returns:
        dict[str, dict[str | None] | None]: Dictionary of metrics containing the names of the value dimensions.
        If the short display name of the value_dimension is not present it returns the result of get_values_display_names().

    Raises:
        TypeError: If `timeseries_object` is not a DataFrame.
        ValueError: If any metric contains more than one value_dimension

    Examples:
    >>> attr = { "by_metric": { "metric1": "value_dimension": {"value_dim_1" : {"unit": "m"}}},
    ...                       { "metric2": "value_dim_1": {"name": "name_of_value_dim_1"}},
    ...                       { "metric3" : "value_dim_1": {}}
    ...    dataframe = pd.DataFrame()
    ...    dataframe.attrs = attr
    ...    get_unit_by_metric(dataframe)
    { "metric1": "m", "metric2": None, "metric3: "km" }
    """
    return defaultdict(lambda: None)
