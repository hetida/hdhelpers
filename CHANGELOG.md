## [Unreleased]
- Update python versions to fix CA certificate issue (https://emudhra.we-have-a-problem.com/)
- metadata accessors can fall back to the properties a metric inherits from objects higher up in an asset hierarchy (under "inherited" in the metric metadata of the current convention), only as last resort after "value_dimensions_shared". This is the default for get_metric_info, get_singlets_metric_info, get_series_info and get_singlets_info. The functions for dedicated information (units, names, display names, short display names and measurements) only do so with keyword argument include_inherited=True, since an inherited property with the same label usually does not describe the metric itself
- get_metric_info and get_singlets_metric_info fall back to the value dimension "value" and to "value_dimensions_shared" if the metric itself does not provide the information
- fix: (short) display names of metadata following the current convention treat null as missing and look up each field on the value dimension, the metric and "value_dimensions_shared" before falling back to the next field. So e.g. a display name of the metric wins over the name of its value dimension
- fix: get_metric_info returns None entries instead of raising if the metadata contains no metric information
- the series accessors determine their metric like the SingleTSFrame accessors: the one given by "single_metric" in the dataset metadata or, if that is missing, the only metric present. The metric named "series" is only used as default for older metadata structures
- a "single_metric" in the dataset metadata which is no string counts as missing. Before, e.g. a list let all accessors of Series and SingleTSFrames raise an error
- fix: get_series_display_name no longer falls back to the short display name, as documented and like get_display_names and get_singlets_display_names
- fix: the SingleTSFrame accessors no longer use the only metric present if it is another one than the metric given by "single_metric" in the dataset metadata. The information counts as missing then
- metadata following the current convention is extracted in a single pass in plain Python instead of evaluating glom specs per level and field. The accessors are considerably faster for frames with many metrics, e.g. about 100 times for 1000 metrics when requesting field names or dotted paths. Other glom specs are still evaluated by glom, but only on the levels needed
- the accessors of Series and SingleTSFrames only resolve the information of their single metric. So they are considerably faster for a Series carrying the metadata of many metrics, e.g. taken from a MultiTSFrame, and a spec is not applied to the other metrics. Also get_series_unit and get_series_name no longer evaluate glom specs for metadata following the current convention. Both are about 90 times faster for the metadata of 1000 metrics
- the requested information is only looked up on the levels needed, so e.g. a spec transforming the information is no longer applied to null values of levels which are not used anyway
- entries of metadata following the current convention which do not adhere to the conventions are skipped: metrics which are no objects or whose field named by the metric key is no string, and value dimensions which are no objects or whose column is no string. "value_dimensions" and "value_dimensions_shared" which are no lists count as empty, a metric key which is no string as missing. Before, a single such entry could make all information missing or raise an error
- new functions get_default_timezones, get_series_default_timezone and get_singlets_default_timezone provide the default time zone of the metrics ("default_timezone" of the current metadata convention), falling back to the one of the dataset metadata. It is meant for computations, e.g. bucketing days when aggregating, not for displaying timestamps, which is what the time zone of the plot target settings is for. New section "Which time zone to compute in?" in the documentation
- documentation: the information requested from get_metric_info, get_singlets_metric_info, get_series_info and get_singlets_info is interpreted as a glom spec. New section "How to query nested information?" with examples for dotted paths into sub dictionaries, other glom specs and keys containing dots
- new class Recording and functions get_recordings, get_series_recording and get_singlets_recording provide how the values of the metrics are recorded: "recording_mode", "data_frequency" with "data_frequency_offset" and "data_frequency_timezone", and "recording_aggregation_method" of the current metadata convention. The frequency falls back to "ref_data_frequency", "ref_data_frequency_offset" and "ref_data_frequency_timezone" of the dataset metadata as a whole, i.e. offset and time zone only apply together with the frequency of the same level. The values are provided as given in the metadata, the documentation of Recording explains what they mean
- new functions get_default_aggregation_methods, get_series_default_aggregation_method and get_singlets_default_aggregation_method provide the default aggregation method of the metrics ("default_aggregation_method"), normalizing "AVG" to "MEAN". Without one, it is "LAST" for metrics whose value dimension "value" has the value data type "boolean" or "string", otherwise "MEAN"
- new function without_metadata provides a copy of a Series or DataFrame without its metadata (attrs) to compute on. pandas deep-copies the attrs to every object an operation creates, which makes e.g. loops over the metrics of a MultiTSFrame with the metadata of many metrics slow. The copy shares the data until it is changed

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
