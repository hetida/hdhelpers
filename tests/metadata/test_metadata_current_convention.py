"""Extraction of metadata following the current metadata convention in a single pass"""

import pandas as pd
import pytest
from glom import Coalesce, Path

import hdhelpers.metadata._current_convention as _current_convention
from hdhelpers.metadata import (
    get_display_names,
    get_metric_info,
    get_series_info,
    get_short_display_names,
    get_singlets_info,
    get_singlets_metric_info,
    get_singlets_units,
    get_units,
)


def frame(attrs):
    df = pd.DataFrame()
    df.attrs = attrs
    return df


def many_metrics_attrs(number):
    return {
        "dataset_metadata": {"metric_key": "id"},
        "metrics": [
            {
                "id": f"m{i}",
                "name": f"Metric {i}",
                "display_name": None,
                "inherited": {"site": "north"},
                "value_dimensions": [{"column": "value", "name": f"Metric {i}", "unit": "m"}],
            }
            for i in range(number)
        ],
    }


def test_entries_not_adhering_to_the_conventions_are_skipped():
    attrs = {
        "metrics": [
            "no object",
            {"name": "without metric key"},
            {"id": None, "name": "null metric key"},
            {"id": 42, "name": "metric key no string"},
            {
                "id": "a",
                "value_dimensions": [
                    {"column": "value", "unit": "m"},
                    {"unit": "without column"},
                    {"column": None, "unit": "null column"},
                    {"column": ["no", "string"], "unit": "column no string"},
                    "no object",
                ],
            },
            {"id": "b", "unit": "m³/h", "value_dimensions": None},
        ],
        "value_dimensions_shared": [
            {"column": "state", "unit": "shared unit"},
            {"unit": "without column"},
            "no object",
        ],
    }

    units = get_units(frame(attrs))

    assert set(units) == {"a", "b"}
    assert units["a"] == {"state": "shared unit", "value": "m"}
    assert units["b"] == {"state": "shared unit", "value": "m³/h"}
    assert set(get_metric_info(frame(attrs), "unit")) == {"a", "b"}


@pytest.mark.parametrize("shared", [None, "no list", {"column": "value", "unit": "m"}])
def test_value_dimensions_shared_which_is_no_list_counts_as_empty(shared):
    attrs = {"metrics": [{"id": "a"}], "value_dimensions_shared": shared}

    assert get_units(frame(attrs)) == {"a": {"value": None}}


@pytest.mark.parametrize("metric_key", [None, 42])
def test_metric_key_which_is_no_string_defaults_to_id(metric_key):
    attrs = {
        "dataset_metadata": {"metric_key": metric_key, "single_metric": "a"},
        "metrics": [{"id": "a", "external_id": "ext", "unit": "m"}],
    }

    assert get_metric_info(frame(attrs), "external_id") == {"a": "ext"}
    assert get_singlets_metric_info(frame(attrs), "unit") == "m"
    assert get_singlets_units(frame(attrs))["value"] == "m"


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        ("name", "n"),
        ("missing", None),
        ("items", None),  # glom does not fall back to attributes of dicts
        (Coalesce("name", default=None), "n"),
        (Coalesce("display_name", "name", default=None), None),  # null display_name is present
        ("sensor.manufacturer", "Acme"),
        ("sensor.missing", None),
        ("display_name.missing", None),  # path through null, left to glom
        ("comments.0.content", "c"),  # list index, left to glom
        ("operator.name", None),  # string paths are split at dots
        (Path("operator.name"), "Ruhrverband"),
        (("comments", ["content"]), ["c"]),
    ],
)
def test_getter_applies_spec_like_glom(spec, expected):
    obj = {
        "name": "n",
        "display_name": None,
        "sensor": {"manufacturer": "Acme"},
        "operator.name": "Ruhrverband",
        "comments": [{"content": "c"}],
    }

    assert _current_convention.getter(spec)(obj) == expected


def test_spec_is_only_applied_to_levels_needed():
    attrs = {
        "metrics": [
            {"id": "a", "name": "Sensor", "value_dimensions": [{"column": "value", "name": None}]}
        ],
        "value_dimensions_shared": [{"column": "value", "name": None}],
    }

    assert get_metric_info(frame(attrs), ("name", str.upper))["a"] == "SENSOR"


def test_unused_inherited_properties_are_not_evaluated():
    attrs = {
        "dataset_metadata": {"single_metric": "a"},
        "metrics": [
            {
                "id": "a",
                "name": "Sensor",
                "inherited": {"name": None},
                "value_dimensions": [{"column": "value", "name": "Value"}],
            }
        ],
    }
    series = pd.Series([1.0])
    series.attrs = attrs

    assert get_series_info(series, ("name", str.upper)) == "VALUE"
    assert get_singlets_info(frame(attrs), ("name", str.upper))["value"] == "VALUE"


def test_no_glom_evaluation_per_metric_for_field_names(monkeypatch):
    """glom costs a lot of time per call, which must not add up for frames with many metrics"""
    calls = []
    original_glom = _current_convention.glom
    monkeypatch.setattr(
        _current_convention,
        "glom",
        lambda *args, **kwargs: calls.append(1) or original_glom(*args, **kwargs),
    )
    multitsframe = frame(many_metrics_attrs(100))

    get_units(multitsframe)
    get_display_names(multitsframe, include_inherited=True)
    get_short_display_names(multitsframe, include_inherited=True)
    get_metric_info(multitsframe, "unit")

    assert calls == []


def test_many_metrics():
    multitsframe = frame(many_metrics_attrs(1000))

    assert get_short_display_names(multitsframe)["m999"]["value"] == "Metric 999"
    assert get_units(multitsframe)["m0"]["value"] == "m"
    assert get_metric_info(multitsframe, "unit")["m500"] == "m"
    assert get_metric_info(multitsframe, "site")["m1"] == "north"
