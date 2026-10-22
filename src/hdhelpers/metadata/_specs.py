from glom import Check, Coalesce, Iter, Merge, Spec, T

# The metadatum specs of the individual accessors, including their fallback chains.
# Defined once here and shared by the MultiTSFrame and the SingleTSFrame accessors, which
# only differ in whether the result is keyed by metric first - not in what they extract.
UNIT: Spec = "unit"
MEASUREMENT: Spec = "measurement"
NAME: Spec = Coalesce("name", default=None)

# The fallback chains of the display names. For metadata following the current metadata
# convention, each field is looked up on all levels (value dimension, metric, shared value
# dimensions) before the next field is tried, see _current_convention.value_dimension_info.
# DISPLAY_NAME and SHORT_DISPLAY_NAME are the corresponding specs for older metadata structures.
DISPLAY_NAME_FIELDS = ("display_name", "name")
SHORT_DISPLAY_NAME_FIELDS = ("short_display_name", *DISPLAY_NAME_FIELDS)
DISPLAY_NAME: Spec = Coalesce(*DISPLAY_NAME_FIELDS, default=None)
SHORT_DISPLAY_NAME: Spec = Coalesce(*SHORT_DISPLAY_NAME_FIELDS, default=None)

# Key of the dict in a metric object holding the properties the metric inherits from objects
# higher up in an asset hierarchy, e.g. the latitude of the plant a sensor belongs to.
INHERITED = "inherited"

# Field of a metric and of the dataset metadata: the time zone the timeseries should be
# evaluated in by default, e.g. for bucketing days when aggregating.
DEFAULT_TIMEZONE = "default_timezone"


def by_metric_key_by_val_dimension(metadatum_key: str | Spec) -> Spec:
    """Provides glom spec that extracts a metadatum by metric by value dimension

    Only for older metadata structures, metadata following the current metadata convention is
    handled by _current_convention.

    The generated glom spec returns a defaultdict of defaultdicts:
        {metric_key: {value_dimension_column_name: metadatum_value}}
    defaulting to None in the inner default dict.

    Properly falls back to respective field in metric metadatum for the "value"
    value_dimension if this value dimension is not explicitely included in the
    metadata of the metric.

    Properly falls back to "value_dimensions_shared" metadata if a value_dimension
    is not given for a metric if its available there.

    metadatum_key can also be any glom spec.
    """
    return Coalesce(
        _spec_platform_convention_series_metric(metadatum_key),
        _spec_platform_convention_series_value_dim(metadatum_key),
        _spec_older_convention1_metric(metadatum_key),
        _spec_older_convention1_value_dim(metadatum_key),
        _spec_older_convention2(metadatum_key),
        _spec_older_convention4(metadatum_key),
        default={},
    )


def _spec_older_convention1_value_dim(metadatum_key: str | Spec) -> Spec:
    return (
        "by_metric",
        Check(instance_of=dict),
        _glom_dict_with_keys_of_current_dict_and_values_something_deeper_nested(
            (
                Coalesce("value_dimensions", default={}),
                Check(instance_of=dict),
                _glom_dict_with_keys_of_current_dict_and_values_something_deeper_nested(
                    Coalesce(metadatum_key)
                ),
            )
        ),
    )


def _spec_older_convention1_metric(metadatum_key: str | Spec) -> Spec:
    return (
        "by_metric",
        Check(instance_of=dict),
        _glom_dict_with_keys_of_current_dict_and_values_something_deeper_nested(
            (
                Coalesce("metric", default={}),
                Check(instance_of=dict),
                {"value": Coalesce(metadatum_key)},
            )
        ),
    )


def _spec_older_convention2(metadatum_key: str | Spec) -> Spec:
    return (
        "metrics",
        Check(instance_of=dict),
        _glom_dict_with_keys_of_current_dict_and_values_something_deeper_nested(
            {"value": Coalesce(metadatum_key, default=None)}  # only SERIES / only value column.
        ),
    )


def _spec_platform_convention_series_metric(metadatum_key: str | Spec) -> Spec:
    return (
        "single_metric_metadata.structured_metadata.metric",
        Check(instance_of=dict),
        {"series": {"value": Coalesce(metadatum_key, default=None)}},
    )


def _spec_platform_convention_series_value_dim(metadatum_key: str | Spec) -> Spec:
    return (
        "single_metric_metadata.structured_metadata.value_dimensions.value",
        Check(instance_of=dict),
        {"series": {"value": Coalesce(metadatum_key, default=None)}},
    )


def _spec_older_convention4(metadatum_key: str | Spec) -> Spec:
    return (
        (
            "metric_metadata",
            Check(instance_of=dict),
            _glom_dict_with_keys_of_current_dict_and_values_something_deeper_nested(
                {"value": Coalesce(metadatum_key, default=None)}  # only SERIES / only value column.
            ),
        ),
    )


def spec_by_metric_key(metadatum_key: str | Spec) -> Spec:
    """Provides glom spec that extracts a metadatum from the metric objects, keyed by metric

    Only for older metadata structures, metadata following the current metadata convention is
    handled by _current_convention.
    """
    return Coalesce(
        (  # some older, simpler metadata structure
            "by_metric",
            _glom_dict_with_keys_of_current_dict_and_values_something_deeper_nested(
                Coalesce(metadatum_key, default=None)
            ),
        ),
        (  # another older / simplified metadata structure
            "metrics",
            _glom_dict_with_keys_of_current_dict_and_values_something_deeper_nested(
                Coalesce(metadatum_key, default=None)
            ),
        ),
    )


def _glom_dict_with_keys_of_current_dict_and_values_something_deeper_nested(
    deeper_glom_spec: Spec,
) -> Spec:
    """Create dicts with keys from current dict and values from deeper in their value objects

    This function provides a glom spec to do this.
    It uses https://glom.readthedocs.io/en/latest/tutorial.html#data-driven-assignment.

    deeper_glom_spec is the spec to get to the deeper values in each value object.

    .. doctest::

        >>> from hdhelpers.metadata._specs import _glom_dict_with_keys_of_current_dict_and_values_something_deeper_nested
        >>> from glom import glom
        >>> data = {
        ...     'some_other_field': 'value',
        ...     'by_item': {
        ...         'item1': {
        ...             'metadata': {
        ...                 'properties': {
        ...                     'unit': 'kg'
        ...                  }
        ...              }
        ...         },
        ...         'item2': {
        ...             'info': {
        ...                 'details': {
        ...                     'unit': 'meters'
        ...                 }
        ...             }
        ...         },
        ...         'item3': {
        ...             'unit': 'liters'
        ...         }
        ...     }
        ... }
        >>> glom(
        ... data,
        ...     ("by_item",
        ...         _glom_dict_with_keys_of_current_dict_and_values_something_deeper_nested(
        ...             Coalesce(
        ...                 "metadata.properties.unit", "info.details.unit", "unit", default=None
        ...             )
        ...         ),
        ...     ),
        ... )
        {'item1': 'kg', 'item2': 'meters', 'item3': 'liters'}
    """
    # T is a stand-in for the target: everything done to T is recorded and executed by glom
    return (
        T.items(),  # treat it as list of (key, value) tuples
        Iter({T[0]: (T[1], deeper_glom_spec)}),
        Merge(),
    )
