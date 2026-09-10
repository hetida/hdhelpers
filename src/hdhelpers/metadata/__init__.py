"""Collection of functions to access metadata information from timeseries objects.
Metadata information can follow varying conventions as the package glom is used to
extract the requested information."""

from hdhelpers.metadata.helpers import (
    get_display_names,
    get_measurements,
    get_metric_info,
    get_names,
    get_queried_interval,
    get_series_display_name,
    get_series_info,
    get_series_measurement,
    get_series_name,
    get_series_short_display_name,
    get_series_unit,
    get_short_display_names,
    get_singlets_display_names,
    get_singlets_info,
    get_singlets_measurements,
    get_singlets_metric_info,
    get_singlets_names,
    get_singlets_short_display_names,
    get_singlets_units,
    get_units,
)

__all__ = [
    "get_queried_interval",
    "get_series_display_name",
    "get_series_measurement",
    "get_series_name",
    "get_series_short_display_name",
    "get_series_unit",
    "get_series_info",
    "get_names",
    "get_short_display_names",
    "get_display_names",
    "get_measurements",
    "get_metric_info",
    "get_units",
    "get_singlets_info",
    "get_singlets_names",
    "get_singlets_short_display_names",
    "get_singlets_display_names",
    "get_singlets_measurements",
    "get_singlets_metric_info",
    "get_singlets_units",
]
