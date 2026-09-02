import datetime

import pandas as pd
import pytest

from hdhelpers.metadata import (
    # get_display_names,
    # get_measurements,
    # get_metric_info,
    get_queried_interval,
    get_series_display_name,
    # get_series_measurement,
    get_series_name,
    get_series_short_display_name,
    get_series_unit,
    # get_units,
    get_singlets_display_names,
    get_singlets_info,
    get_singlets_measurements,
    get_singlets_metric_info,
    get_singlets_names,
    get_singlets_short_display_names,
    get_singlets_units,
)


def test_get_queried_interval(empty_series_with_old_attr_real):
    start, end = get_queried_interval(empty_series_with_old_attr_real)
    assert start == datetime.datetime(2025, 11, 5, 13, 28, tzinfo=datetime.UTC)
    assert end == datetime.datetime(2025, 11, 6, 13, 28, tzinfo=datetime.UTC)


def test_doctest_get_queried_interval():
    attr = {
        "dataset_metadata": {
            "ref_interval_start_timestamp": "2025-11-04T13:28:00Z",
            "ref_interval_end_timestamp": "2025-11-07T13:28:00Z",
        }
    }
    series = pd.Series()
    series.attrs = attr
    start, end = get_queried_interval(series)

    assert start == datetime.datetime(2025, 11, 4, 13, 28, tzinfo=datetime.UTC)
    assert end == datetime.datetime(2025, 11, 7, 13, 28, tzinfo=datetime.UTC)


def test_get_queried_interval_not_given():
    start, end = get_queried_interval(pd.Series())

    assert start is None
    assert end is None


def test_get_series_unit(empty_series_with_old_attr_real):
    unit = get_series_unit(empty_series_with_old_attr_real)
    assert unit == "m³/s"


@pytest.mark.parametrize(
    ("attr", "output"),
    [
        pytest.param(
            {"single_metric_metadata": {"structured_metadata": {"value_dimensions": {}}}},
            None,
            id="value not given",
        ),
        pytest.param(
            {
                "single_metric_metadata": {
                    "structured_metadata": {"value_dimensions": {"value": {"unit": None}}}
                }
            },
            None,
            id="unit not given",
        ),
        pytest.param(
            {
                "single_metric_metadata": {
                    "structured_metadata": {"value_dimensions": {"value": {"unit": "m/s"}}}
                }
            },
            "m/s",
            id="given",
        ),
    ],
)
def test_doctest_get_series_unit(attr, output):
    series = pd.Series()
    series.attrs = attr
    assert get_series_unit(series) == output


def test_get_series_unit_no_attr():
    assert get_series_unit(pd.Series()) is None


def test_get_series_name(empty_series_with_old_attr_real):
    name = get_series_name(empty_series_with_old_attr_real)
    assert name == "Wasserstand"


@pytest.mark.parametrize(
    ("attr", "output"),
    [
        pytest.param(
            {
                "single_metric_metadata": {
                    "structured_metadata": {
                        "value_dimensions": {"value": {"name": "value_name_of_series"}}
                    }
                }
            },
            "value_name_of_series",
            id="value name",
        ),
        pytest.param(
            {
                "single_metric_metadata": {
                    "structured_metadata": {"metric": {"name": "name_of_series"}}
                }
            },
            "name_of_series",
            id="name_of_series",
        ),
        pytest.param(
            {
                "single_metric_metadata": {
                    "structured_metadata": {
                        "metric": {"name": "name_of_series"},
                        "value_dimensions": {"value": {"name": "value_name_of_series"}},
                    }
                }
            },
            "name_of_series",
            id="metric before value",
        ),
    ],
)
def test_doctest_get_series_name(attr, output):
    series = pd.Series()
    series.attrs = attr
    assert get_series_name(series) == output


def test_get_series_name_no_attr():
    assert get_series_name(pd.Series()) is None


def test_get_display_name_series_name(empty_series_with_old_attr_real):
    display_name = get_series_display_name(empty_series_with_old_attr_real)
    assert display_name == "Wasserstand"


@pytest.mark.parametrize(
    ("attr", "output"),
    [
        pytest.param(
            {"by_metric": {"series": {"metric": {"display_name": "metric_display_name"}}}},
            "metric_display_name",
            id="metric_display_name",
        ),
        pytest.param(
            {
                "by_metric": {
                    "series": {
                        "value_dimensions": {"value": {"display_name": "value_display_name"}}
                    }
                }
            },
            "value_display_name",
            id="value_display_name",
        ),
        pytest.param(
            {
                "by_metric": {
                    "series": {
                        "metric": {"display_name": "metric_display_name"},
                        "value_dimensions": {"value": {"display_name": "value_display_name"}},
                    }
                }
            },
            "metric_display_name",
            id="metric before value",
        ),
        pytest.param(
            {
                "by_metric": {
                    "series": {
                        "metric": {"name": "metric_name"},
                        "value_dimensions": {"value": {"display_name": "value_display_name"}},
                    }
                }
            },
            "metric_name",
            id="metric name before value display name",
        ),
        pytest.param(
            {
                "by_metric": {
                    "series": {
                        "metric": {"name": "metric_name"},
                        "value_dimensions": {"value": {"name": "value_name"}},
                    }
                }
            },
            "metric_name",
            id="metric name before value name",
        ),
        pytest.param(
            {
                "single_metric_metadata": {
                    "structured_metadata": {"metric": {"display_name": "metric_display_name"}}
                }
            },
            "metric_display_name",
            id="metric_display_name platform",
        ),
        pytest.param(
            {
                "single_metric_metadata": {
                    "structured_metadata": {
                        "value_dimensions": {"value": {"display_name": "value_display_name"}}
                    }
                }
            },
            "value_display_name",
            id="value_display_name platform",
        ),
        pytest.param(
            {
                "single_metric_metadata": {
                    "structured_metadata": {
                        "metric": {"display_name": "metric_display_name"},
                        "value_dimensions": {"value": {"display_name": "value_display_name"}},
                    }
                }
            },
            "metric_display_name",
            id="metric before value platform",
        ),
        pytest.param(
            {
                "single_metric_metadata": {
                    "structured_metadata": {
                        "metric": {"name": "metric_display_name"},
                        "value_dimensions": {"value": {"display_name": "value_display_name"}},
                    }
                }
            },
            "metric_display_name",
            id="metric before value name platform",
        ),
        pytest.param(
            {
                "single_metric_metadata": {
                    "structured_metadata": {
                        "metric": {"name": "metric_name"},
                        "value_dimensions": {"value": {"name": "value_name"}},
                    }
                }
            },
            "metric_name",
            id="metric name before value name platform",
        ),
    ],
)
def test_doctest_get_series_display_name(attr, output):
    series = pd.Series()
    series.attrs = attr
    assert get_series_display_name(series) == output


def test_get_series_display_name_no_attr():
    assert get_series_display_name(pd.Series()) is None


def test_get_short_display_name_series_name(empty_series_with_old_attr_real):
    display_name = get_series_short_display_name(empty_series_with_old_attr_real)
    assert display_name == "W"


@pytest.mark.parametrize(
    ("attr", "output"),
    [
        pytest.param(
            {
                "single_metric_metadata": {
                    "structured_metadata": {
                        "metric": {"short_display_name": "short_display_name_of_series"}
                    }
                }
            },
            "short_display_name_of_series",
            id="metric_short_display_name",
        ),
        pytest.param(
            {
                "single_metric_metadata": {
                    "structured_metadata": {
                        "value_dimensions": {
                            "value": {"short_display_name": "value_short_display_name"}
                        }
                    }
                }
            },
            "value_short_display_name",
            id="value_short_display_name",
        ),
        pytest.param(
            {
                "single_metric_metadata": {
                    "structured_metadata": {
                        "metric": {"short_display_name": "metric_short_display_name"},
                        "value_dimensions": {
                            "value": {"short_display_name": "value_short_display_name"}
                        },
                    }
                }
            },
            "metric_short_display_name",
            id="metric before value",
        ),
        pytest.param(
            {
                "single_metric_metadata": {
                    "structured_metadata": {
                        "metric": {"name": "metric_name"},
                        "value_dimensions": {"value": {"display_name": "value_display_name"}},
                    }
                }
            },
            "metric_name",
            id="metric display name before value name",
        ),
        pytest.param(
            {
                "single_metric_metadata": {
                    "structured_metadata": {
                        "metric": {"name": "metric_name"},
                        "value_dimensions": {"value": {"name": "value_name"}},
                    }
                }
            },
            "metric_name",
            id="metric name before value name",
        ),
    ],
)
def test_doctest_get_series_short_display_name(attr, output):
    series = pd.Series()
    series.attrs = attr
    assert get_series_short_display_name(series) == output


def test_get_names_for_mts_with_metric_info_fallback_option():
    from hdhelpers.metadata import get_display_names, get_names, get_short_display_names

    attr = {
        "by_metric": {
            "metric1": {"metric": {"name": "name_of_metric1"}},
            "metric2": {"metric": {"name": None}},
        }
    }

    attr = {
        "by_metric": {
            "metric1": {"metric": {"short_display_name": "short_display_name_of_metric1"}},
            "metric2": {"metric": {"name": "name_of_metric2"}},
            "metric3": {},
        }
    }

    attr = {
        "dataset_metadata": {"metric_key": "column"},
        "metrics": [
            {
                "external_id": "column_name",
                "value_dimensions": [{"column": "temp", "measurement": "temperature"}],
            }
        ],
    }

    dataframe = pd.DataFrame()
    dataframe.attrs = attr
    result_name = get_names(dataframe)
    result_display_name = get_display_names(dataframe)
    result_short_display_name = get_short_display_names(dataframe)

    assert result_name == result_display_name == result_short_display_name


def test_get_singlets_info_is_keyed_by_value_dimension_only(empty_singletsframe_with_attr):
    """A SingleTSFrame has one metric, so no metric level in the result"""
    units = get_singlets_units(empty_singletsframe_with_attr)

    assert units["value"] == "°C"
    assert units["state"] == "UNKNOWN"  # falls back to value_dimensions_shared
    assert units["not-given"] is None


def test_get_singlets_names(empty_singletsframe_with_attr):
    names = get_singlets_names(empty_singletsframe_with_attr)

    assert names["value"] == "temperature"
    assert names["state"] == "measurement state"
    assert names["not-given"] is None


def test_get_singlets_display_names_fall_back_to_name(empty_singletsframe_with_attr):
    empty_singletsframe_with_attr.attrs["metrics"][0]["value_dimensions"][0]["display_name"] = (
        "temp"
    )

    display_names = get_singlets_display_names(empty_singletsframe_with_attr)

    assert display_names["value"] == "temp"
    assert display_names["state"] == "measurement state"


def test_get_singlets_short_display_names_fall_back(empty_singletsframe_with_attr):
    empty_singletsframe_with_attr.attrs["metrics"][0]["value_dimensions"][0][
        "short_display_name"
    ] = "T"
    empty_singletsframe_with_attr.attrs["metrics"][0]["value_dimensions"][1]["display_name"] = (
        "state"
    )

    short_display_names = get_singlets_short_display_names(empty_singletsframe_with_attr)

    assert short_display_names["value"] == "T"
    assert short_display_names["state"] == "state"


def test_get_singlets_measurements(empty_singletsframe_with_attr):
    empty_singletsframe_with_attr.attrs["metrics"][0]["value_dimensions"][0]["measurement"] = (
        "temperature"
    )

    measurements = get_singlets_measurements(empty_singletsframe_with_attr)

    assert measurements["value"] == "temperature"
    assert measurements["state"] is None


def test_get_singlets_info_with_arbitrary_spec(empty_singletsframe_with_attr):
    assert get_singlets_info(empty_singletsframe_with_attr, "unit")["value"] == "°C"
    assert get_singlets_info(empty_singletsframe_with_attr, "not-given")["value"] is None


def test_get_singlets_metric_info(empty_singletsframe_with_attr):
    assert get_singlets_metric_info(empty_singletsframe_with_attr, "name") == "ABC temperature"
    assert get_singlets_metric_info(empty_singletsframe_with_attr, "external_id") == "abc.temp"
    assert get_singlets_metric_info(empty_singletsframe_with_attr, "not-given") is None


def test_get_singlets_metric_key_defaults_to_id():
    """metric_key is optional per convention and defaults to "id" """
    empty_singletsframe_with_attr = pd.DataFrame()
    empty_singletsframe_with_attr.attrs = {
        "dataset_metadata": {"single_metric": "abc.temp"},
        "metrics": [{"id": "abc.temp", "value_dimensions": [{"column": "value", "unit": "m"}]}],
    }

    assert get_singlets_units(empty_singletsframe_with_attr)["value"] == "m"
    assert get_singlets_metric_info(empty_singletsframe_with_attr, "id") == "abc.temp"


def test_get_singlets_falls_back_to_only_metric_without_single_metric(
    empty_singletsframe_with_attr,
):
    """If single_metric is missing but there is exactly one metric, use that one"""
    del empty_singletsframe_with_attr.attrs["dataset_metadata"]["single_metric"]

    assert get_singlets_units(empty_singletsframe_with_attr)["value"] == "°C"
    assert get_singlets_metric_info(empty_singletsframe_with_attr, "name") == "ABC temperature"


def test_get_singlets_without_metadata():
    """Components should not require metadata, so no metadata must not raise"""
    empty_singletsframe_with_attr = pd.DataFrame()

    assert get_singlets_units(empty_singletsframe_with_attr)["value"] is None
    assert get_singlets_names(empty_singletsframe_with_attr)["value"] is None
    assert get_singlets_display_names(empty_singletsframe_with_attr)["value"] is None
    assert get_singlets_short_display_names(empty_singletsframe_with_attr)["value"] is None
    assert get_singlets_measurements(empty_singletsframe_with_attr)["value"] is None
    assert get_singlets_metric_info(empty_singletsframe_with_attr, "name") is None


@pytest.mark.parametrize(
    "func",
    [
        get_singlets_units,
        get_singlets_names,
        get_singlets_display_names,
        get_singlets_short_display_names,
        get_singlets_measurements,
    ],
)
def test_get_singlets_requires_a_dataframe(func):
    with pytest.raises(TypeError):
        func(pd.Series())
