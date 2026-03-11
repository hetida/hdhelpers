from collections import defaultdict
from collections.abc import Callable

from glom import A, Check, Coalesce, Iter, Merge, S, Spec, T, glom

def by_metric_key_by_val_dimension(metadatum_key: str | Spec) -> Spec:
    """Providesglom spec that extracts a metadatum by metric by value dimension

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
        _spec_new_convention(metadatum_key),
        _spec_platform_convention_series_metric(metadatum_key),
        _spec_platform_convention_series_value_dim(metadatum_key),
        _spec_older_convention1_metric(metadatum_key),
        _spec_older_convention1_value_dim(metadatum_key),
        _spec_older_convention2(metadatum_key),
        _spec_older_convention4(metadatum_key),
        default={},
    )

def _spec_metric_key() -> Spec:
    return ("dataset_metadata.metric_key", A.globals.metric_key)


def _spec_defaults_by_value_dimension(metadatum_key: str | Spec) -> Spec:
    return Coalesce(
        (
            Coalesce("value_dimensions_shared", default=[]),
            Check(instance_of=list),
            build_dict_from_iterable_from_key_and_subspec_and_then_proceed_on_result(
                "column", Coalesce(metadatum_key, default=None)
            ),
        ),
        default={},
    )


def _spec_defaults_by_metric(metadatum_key: str | Spec) -> Spec:
    return Coalesce(
        (
            "metrics",
            Check(instance_of=list),
            build_dict_from_iterable_from_key_and_subspec_and_then_proceed_on_result(
                S.globals.metric_key,
                Coalesce(metadatum_key, default=None),
                key_as_value=True,
            ),
        ),
        default={},
    )


def _spec_actual_per_metric_per_value_dimensions(metadatum_key: str | Spec) -> Spec:
    return Coalesce(
        (
            "metrics",
            Check(instance_of=list),
            _build_dict_from_iterable_from_key_and_subspec_and_then_proceed_on_result(
                S.globals.metric_key,
                (
                    Coalesce("value_dimensions", default={}),
                    _build_dict_from_iterable_from_key_and_subspec_and_then_proceed_on_result(
                        "column",
                        Coalesce(metadatum_key, default=None),
                        add_keys_with_none_values=["value"],
                    ),
                ),
                key_as_value=True,
            ),
        ),
        default={},
    )


def _spec_new_convention(metadatum_key: str | Spec) -> Spec:
    return (
        {  # first gather information at different locations in metadata in a dict
            "metric_key": _spec_metric_key(),
            "defaults_by_value_dimension": _spec_defaults_by_value_dimension(metadatum_key),
            "defaults_by_metric": _spec_defaults_by_metric(metadatum_key),
            "actual_per_metric_per_value_dimensions": _spec_actual_per_metric_per_value_dimensions(
                metadatum_key
            ),
        },
        lambda x: defaultdict(
            lambda: defaultdict(lambda: None, {}),
            {  # combine dicts with gathered information / falling back to defaults
                metric: defaultdict(
                    lambda: None,
                    {
                        value_dim: info
                        if info is not None  # prio 1: use, if explicitely provided
                        else (
                            x["defaults_by_metric"][metric]
                            if (
                                value_dim == "value"
                                and x["defaults_by_metric"].get(metric) is not None
                            )  # prio 2: only for "value" value dim: possibly use from metric
                            else (
                                x["defaults_by_value_dimension"].get(
                                    value_dim, None
                                )  # prio 3: from global "value_dimensions_shared"
                            )
                        )
                        for value_dim, info in _update_dict_and_return_it(
                            x["defaults_by_value_dimension"].copy(), info_by_val_dim
                        ).items()
                    },
                )
                for metric, info_by_val_dim in x["actual_per_metric_per_value_dimensions"].items()
            },
        ),
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

def _spec_by_metric_key(metadatum_key: str | Spec) -> Spec:
    return Coalesce(
        (  # current metdadata convention
            {
                "metric_key": ("dataset_metadata.metric_key", A.globals.metric_key),
                "by_metric": (
                    "metrics",
                    Check(instance_of=list),
                    _build_dict_from_iterable_from_key_and_subspec_and_then_proceed_on_result(
                        S.globals.metric_key,
                        Coalesce(metadatum_key, default=None),
                        key_as_value=True,
                    ),
                ),
            },
            lambda x: defaultdict(lambda: None, x["by_metric"]),
        ),
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

def _build_dict_from_iterable_from_key_and_subspec_and_then_proceed_on_result(
    key_spec: Spec,
    value_spec: Spec,
    add_keys_with_none_values: list[str] | None = None,
    default_dict_func: Callable | None = None,
    continuation_spec: Spec | None = None,
    key_as_value: bool = False,
) -> Spec:
    """Build dict from an iterable

    Spec to convert an iterable of objects to a dict using one of their fields
    (or something deeper) as keys and something else as values.

    The key something and the value something can be arbitrary specs that are applyable
    on each item.

    The resulting glom spec first produces a dictionary which keys being extracted from
    each element of the iterable using key_spec and values using value_spec.

    If given it then proceeds on the resulting object using the continuation_spec.

    add_keys_with_none_values allows to add keys even if they do not occur
    with a default value of None.

    Example:

    data = {
        "some": [
            {"id": 42, "name": "some_name", "sub": {"unit": "l"}},
            {"id": 53, "name": "another", "sub": {"unit": "m"}},
        ]
    }

    glom(
        data,
        (
            "some",
            build_dict_from_iterable_from_key_and_subspec_and_then_proceed_on_result(
                "id", "sub.unit"
            ),
        ),
    )

    # yields:
    {42: 'l', 53: 'm'}
    """
    if add_keys_with_none_values is None:
        add_keys_with_none_values = []

    start_dict = dict.fromkeys(add_keys_with_none_values, None)

    if default_dict_func is not None:
        start_dict = defaultdict(default_dict_func, start_dict)

    return (
        [{"key": key_spec if not key_as_value else T[key_spec], "value": value_spec}],
        [lambda x: (x["key"], x["value"])],
        dict,
        lambda x: _update_dict_and_return_it(start_dict.copy(), x),
    ) + ((continuation_spec,) if continuation_spec is not None else ())

def glom_dict_with_keys_of_current_dict_and_values_something_deeper_nested(
    deeper_glom_spec: Spec, add_keys_with_none_values: list[str] | None = None
) -> Spec:
    """Create dicts with keys from current dict and values from deeper in their value objects

    This function provides a glom spec to do this.
    It uses https://glom.readthedocs.io/en/latest/tutorial.html#data-driven-assignment.

    deeper_glom_spec is the spec to get to the deeper values in each value object.

    add_keys_with_none_values allows to add keys even if they do not occur
    with a default value of None.


    E.g.

    data = {
        'some_other_field': 'value',
        'by_item': {
            'item1': {
                'metadata': {
                    'properties': {
                        'unit': 'kg'
                    }
                }
            },
            'item2': {
                'info': {
                    'details': {
                        'unit': 'meters'
                    }
                }
            },
            'item3': {
                'unit': 'liters'
            }
        }
    }

    res = glom(
        data,
        (
            "by_item",
            glom_dict_with_keys_of_current_dict_and_values_something_deeper_nested(
                Coalesce(
                    "metadata.properties.unit", "info.details.unit", "unit", default=None
                )
            ),
        ),
    )
    print(res)
    # will output:
    #     {'item1': 'kg', 'item2': 'meters', 'item3': 'liters'}

    """
    if add_keys_with_none_values is None:
        add_keys_with_none_values = []

    start_dict = dict.fromkeys(add_keys_with_none_values, None)

    return (
        T.items(),  # treat it as list of (key, value) tuples
        Iter({T[0]: (T[1], deeper_glom_spec)}),
        Merge(),
        lambda x: _update_dict_and_return_it(start_dict.copy(), x),
    )

# info on T: Basically, think of T as your data’s stunt double. Everything that you do to T will be recorded and executed during the glom() call.
# info to S: On its surface, the glom scope is a dictionary of extra values that can be passed in to the top-level glom call. These values can then be addressed with the S object, which behaves similarly to the T object.
# info on A: Any keyword arguments to the S will have their values evaluated as a spec, with the result being saved to the keyword argument name in the scope. When only the target is being assigned, you can use the A as a shortcut
def _update_dict_and_return_it(start_dict: dict, updated_values_dict: dict) -> dict:
    """Update a dict and return it"""
    start_dict.update(updated_values_dict)
    return start_dict
