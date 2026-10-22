## [Unreleased]
- metadata accessors can fall back to the properties a metric inherits from objects higher up in an asset hierarchy (under "inherited" in the metric metadata of the current convention), only as last resort after "value_dimensions_shared". This is the default for get_metric_info, get_singlets_metric_info, get_series_info and get_singlets_info. The functions for dedicated information (units, names, display names, short display names and measurements) only do so with keyword argument include_inherited=True, since an inherited property with the same label usually does not describe the metric itself
- get_metric_info and get_singlets_metric_info fall back to the value dimension "value" and to "value_dimensions_shared" if the metric itself does not provide the information
- fix: (short) display names of metadata following the current convention treat null as missing and look up each field on the value dimension, the metric and "value_dimensions_shared" before falling back to the next field. So e.g. a display name of the metric wins over the name of its value dimension
- fix: get_metric_info returns None entries instead of raising if the metadata contains no metric information
- the series accessors use the only metric if "single_metric" is missing in the dataset metadata
- fix: the SingleTSFrame accessors no longer use the only metric present if it is another one than the metric given by "single_metric" in the dataset metadata. The information counts as missing then
- metadata following the current convention is extracted in a single pass in plain Python instead of evaluating glom specs per level and field. The accessors are considerably faster for frames with many metrics, e.g. about 100 times for 1000 metrics when requesting field names or dotted paths. Other glom specs are still evaluated by glom, but only on the levels needed
- the requested information is only looked up on the levels needed, so e.g. a spec transforming the information is no longer applied to null values of levels which are not used anyway
- entries of metadata following the current convention which do not adhere to the conventions are skipped: metrics which are no objects or whose field named by the metric key is no string, and value dimensions which are no objects or whose column is no string. "value_dimensions" and "value_dimensions_shared" which are no lists count as empty, a metric key which is no string as missing. Before, a single such entry could make all information missing or raise an error
- new functions get_default_timezones, get_series_default_timezone and get_singlets_default_timezone provide the default time zone of the metrics ("default_timezone" of the current metadata convention), falling back to the one of the dataset metadata. It is meant for computations, e.g. bucketing days when aggregating, not for displaying timestamps, which is what the time zone of the plot target settings is for. New section "Which time zone to compute in?" in the documentation
- documentation: the information requested from get_metric_info, get_singlets_metric_info, get_series_info and get_singlets_info is interpreted as a glom spec. New section "How to query nested information?" with examples for dotted paths into sub dictionaries, other glom specs and keys containing dots

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
