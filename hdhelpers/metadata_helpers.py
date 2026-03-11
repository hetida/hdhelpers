from collections import defaultdict
from typing import Any

import pandas as pd
from glom import A, Check, glom

import metadata_specs as specs


def spec_not_none(spec: str | Spec) -> Spec:
    """this entries must be given in the spec"""
    # TODO: Given the suite of tools introduced with Match, the Check specifier type may be deprecated in a future release
    return (spec, Check(validate=lambda x: x is not None))


def get_value_dimension_info(
    multitsframe: pd.DataFrame | pd.Series, value_dim_info: str | Spec
) -> defaultdict[str, defaultdict[str, Any]]:
    """Obtain metadata info associated to the value dimensions of the metrics

    Returns a default dict whose values are the entries of the metrics metadata specified via
    "metric_key" in "dataset_metadata".

    Its values are defaultdicts whose keys are the "column" entries of the value dimension
    objects of that metric and whose values are extracted from the value_dimension object
    using using value_dim_info as a glom Spec, typically just a subfield.

    For the default "value" value dimension, if no concrete / explicit information is available
    for this value dimension, a corresponding entry in the metric object may be used.

    For all value dimensions, if no concrete explicit information is available for that value
    dimension in the value_dimensions list under the metric, the global "value_dimensions_shared"
    field of the attrs object is searched for corresponding information.

    If no information is found, None is set as value and is the default value of the
    inner default dict.

    For examples we refer to the corresponding unit tests (/tests/helpers/test_metadata.py).
    """
    spec = specs.by_metric_key_by_val_dimension(value_dim_info)
    value_dimension_info_by_metric_by_value_dimension = glom(multitsframe.attrs, spec)
    return defaultdict(
        lambda: defaultdict(lambda: None), value_dimension_info_by_metric_by_value_dimension
    )
