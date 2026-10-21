## [Unreleased]
- metadata accessors can fall back to the properties a metric inherits from objects higher up in an asset hierarchy (under "inherited" in the metric metadata of the current convention), only as last resort after "value_dimensions_shared". This is the default for get_metric_info, get_singlets_metric_info, get_series_info and get_singlets_info. The functions for dedicated information (units, names, display names, short display names and measurements) only do so with keyword argument include_inherited=True, since an inherited property with the same label usually does not describe the metric itself
- get_metric_info and get_singlets_metric_info fall back to the value dimension "value" and to "value_dimensions_shared" if the metric itself does not provide the information
- fix: (short) display names of metadata following the current convention treat null as missing and look up each field on the value dimension, the metric and "value_dimensions_shared" before falling back to the next field. So e.g. a display name of the metric wins over the name of its value dimension
- fix: get_metric_info returns None entries instead of raising if the metadata contains no metric information
- the series accessors use the only metric if "single_metric" is missing in the dataset metadata

## [0.0.9] - 2026-09-10
- singletsframe support

## [0.0.8] - 2026-07-07
- add new plotting-module to wheel

## [0.0.7] - 2026-07-07
- fix circular import
- set pandas dependency >= 3
- minor improvement in tick formats

## [0.0.6] - 2026-07-06
- add color, locale, Plotly theme, timestamp ticks

## [0.0.5] - 2026-07-06
- Nothing changed

## [0.0.4] - 2026-06-25
- Avoid RangeIndex being modified in modify_timezone
- Enhance documentation of modify_timezone

## [0.0.3] - 2026-06-23
- Fixes in modify_timezone
- Disarm dependencies to ease compatibility to designer development
- Enhance documentation

## [0.0.2] - 2026-05-21
- Include helpers for metadata
- Include helper function for modify timezone
- Publish sphinx documentation on GitHub Pages

## [0.0.1] - 2025-09-11
- Test upload on pypi of hdhelpers
- Note: No tagging used as it was only a test upload on pypi
