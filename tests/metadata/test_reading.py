"""Lookups with the fallbacks of the conventions and changed versions of the models"""

import datetime
from typing import Any

import pytest
from pydantic import ValidationError

from hdhelpers.metadata._reading import Recording
from hdhelpers.metadata.conventions import (
    MetadataConventionError,
    MultiTSFrameMetadata,
    SeriesMetadata,
    SingleTSFrameMetadata,
)


def value_dimension(column: str = "value", **fields: Any) -> dict[str, Any]:
    return {"column": column, "unit": None, "measurement": None} | fields


def metric(metric_id: str, **fields: Any) -> dict[str, Any]:
    return {
        "id": metric_id,
        "name": f"name of {metric_id}",
        "value_dimensions": [value_dimension()],
    } | fields


def dataset_metadata(**fields: Any) -> dict[str, Any]:
    return {
        "metric_key": "id",
        "queried_metrics": [],
        "ref_interval_start_timestamp": "2026-10-18T00:00:00Z",
        "ref_interval_end_timestamp": "2026-10-19T00:00:00+00:00",
        "ref_interval_type": "closed",
    } | fields


def multitsframe(*metrics: dict[str, Any], **fields: Any) -> MultiTSFrameMetadata:
    return MultiTSFrameMetadata.model_validate(
        {"dataset_metadata": dataset_metadata(), "metrics": list(metrics)} | fields
    )


def series(metric_fields: dict[str, Any], **dataset_fields: Any) -> SeriesMetadata:
    return SeriesMetadata.model_validate(
        {
            "dataset_metadata": dataset_metadata(
                single_metric="s", queried_metrics=["s"], **dataset_fields
            ),
            "metrics": [metric("s", **metric_fields)],
        }
    )


class TestMetrics:
    def test_metric_ids_in_order(self) -> None:
        meta = multitsframe(metric("b"), metric("a"))

        assert meta.metric_ids() == ["b", "a"]
        assert meta.metric("a").name == "name of a"

    def test_metric_key_names_the_id(self) -> None:
        meta = MultiTSFrameMetadata.model_validate(
            {
                "dataset_metadata": dataset_metadata(metric_key="tag"),
                "metrics": [metric("m1", tag="plant.temperature")],
            }
        )

        assert meta.metric_ids() == ["plant.temperature"]

    def test_unknown_metric(self) -> None:
        meta = multitsframe(metric("a"))

        with pytest.raises(KeyError):
            meta.metric("b")
        assert meta.unit("b") is None
        assert meta.metric_info("name", "b") is None

    def test_multitsframe_requires_metric_id(self) -> None:
        with pytest.raises(TypeError, match="metric_id"):
            multitsframe(metric("a")).unit()

    def test_single_metric_by_default(self) -> None:
        meta = series({"value_dimensions": [value_dimension(unit="m")]})

        assert meta.metric().id == "s"
        assert meta.unit() == "m"
        assert meta.unit("s") == "m"

    def test_singletsframe_columns(self) -> None:
        meta = SingleTSFrameMetadata.model_validate(
            {
                "dataset_metadata": dataset_metadata(single_metric="f", queried_metrics=["f"]),
                "metrics": [
                    metric(
                        "f",
                        value_dimensions=[
                            value_dimension("temperature", unit="°C"),
                            value_dimension("pressure", unit="bar"),
                        ],
                    )
                ],
            }
        )

        assert meta.unit(column="pressure") == "bar"
        assert meta.units() == {"f": {"value": None, "temperature": "°C", "pressure": "bar"}}


class TestValueDimensionInformation:
    def test_value_dimension_first(self) -> None:
        meta = series({"unit": "metric unit", "value_dimensions": [value_dimension(unit="m")]})

        assert meta.unit() == "m"

    def test_metric_for_value(self) -> None:
        meta = series({"unit": "m"})

        assert meta.unit() == "m"

    def test_metric_not_for_other_columns(self) -> None:
        meta = multitsframe(
            metric("a", unit="m", value_dimensions=[value_dimension("other")]),
        )

        assert meta.units() == {"a": {"value": "m", "other": None}}

    def test_shared_value_dimensions_last(self) -> None:
        meta = multitsframe(
            metric("a", value_dimensions=[value_dimension("temperature", unit="K")]),
            metric("b", value_dimensions=[value_dimension("temperature")]),
            value_dimensions_shared=[
                value_dimension("temperature", unit="°C"),
                value_dimension("pressure", unit="bar"),
            ],
        )

        assert meta.units() == {
            "a": {"temperature": "K", "pressure": "bar", "value": None},
            "b": {"temperature": "°C", "pressure": "bar", "value": None},
        }
        assert meta.unit("b", "temperature") == "°C"

    def test_each_field_on_all_levels_before_the_next(self) -> None:
        meta = series({"display_name": "metric display name"})

        # the display name of the metric wins over the name of the value dimension
        assert meta.display_name() == "metric display name"
        assert meta.short_display_name() == "metric display name"
        assert meta.name() == "name of s"

    def test_display_name_falls_back_to_name(self) -> None:
        meta = series({"value_dimensions": [value_dimension(name="level")]})

        assert meta.display_name() == "level"
        assert meta.short_display_name() == "level"

    def test_null_counts_as_missing(self) -> None:
        meta = series(
            {"display_name": None, "value_dimensions": [value_dimension(display_name=None)]}
        )

        assert meta.display_name() == "name of s"

    def test_inherited_properties_only_on_request(self) -> None:
        meta = series({"inherited": {"unit": "m", "measurement": "level"}})

        assert meta.unit() is None
        assert meta.unit(include_inherited=True) == "m"
        assert meta.measurements(include_inherited=True) == {"s": {"value": "level"}}

    def test_inherited_properties_only_for_value(self) -> None:
        meta = multitsframe(
            metric("a", inherited={"unit": "m"}, value_dimensions=[value_dimension("other")])
        )

        assert meta.units(include_inherited=True) == {"a": {"value": "m", "other": None}}

    def test_extra_fields_and_dotted_paths(self) -> None:
        meta = series({"value_dimensions": [value_dimension(sensor={"model": "X1"})]})

        assert meta.value_dimension_info("sensor.model") == "X1"
        assert meta.value_dimension_info("sensor.serial") is None
        assert meta.value_dimension_info(["sensor.serial", "sensor.model"]) == "X1"


class TestMetricInformation:
    def test_fallbacks(self) -> None:
        meta = multitsframe(
            metric("own", description="own"),
            metric("value", value_dimensions=[value_dimension(description="value")]),
            metric("shared"),
            metric("inherited", inherited={"description": "inherited"}),
            value_dimensions_shared=[value_dimension(description="shared")],
        )

        assert meta.metric_infos("description") == {
            "own": "own",
            "value": "value",
            "shared": "shared",
            "inherited": "shared",
        }

    def test_inherited_properties_by_default(self) -> None:
        meta = series({"inherited": {"site": "north"}})

        assert meta.metric_info("site") == "north"
        assert meta.metric_info("site", include_inherited=False) is None


class TestTimezonesRecordingAggregation:
    def test_default_timezone(self) -> None:
        meta = MultiTSFrameMetadata.model_validate(
            {
                "dataset_metadata": dataset_metadata(default_timezone="UTC"),
                "metrics": [metric("a", default_timezone="Europe/Berlin"), metric("b")],
            }
        )

        assert meta.default_timezones() == {"a": "Europe/Berlin", "b": "UTC"}
        assert meta.default_timezone("unknown") == "UTC"

    def test_recording_falls_back_as_a_whole(self) -> None:
        meta = MultiTSFrameMetadata.model_validate(
            {
                "dataset_metadata": dataset_metadata(
                    ref_data_frequency="1h",
                    ref_data_frequency_offset="5min",
                    ref_data_frequency_timezone="Europe/Berlin",
                ),
                "metrics": [
                    metric(
                        "own",
                        recording_mode="periodic",
                        data_frequency="15min",
                        recording_aggregation_method="MAX",
                    ),
                    metric("dataset", recording_mode="on_change"),
                ],
            }
        )

        assert meta.recordings() == {
            "own": Recording("periodic", "15min", None, None, "MAX"),
            "dataset": Recording("on_change", "1h", "5min", "Europe/Berlin", None),
        }
        assert meta.recording("unknown") == Recording(None, "1h", "5min", "Europe/Berlin", None)
        assert type(meta.recording("own").recording_mode) is str

    @pytest.mark.parametrize(
        ("metric_fields", "shared", "expected"),
        [
            ({"default_aggregation_method": "MAX"}, None, "MAX"),
            ({"default_aggregation_method": "AVG"}, None, "MEAN"),
            ({"value_dimensions": [value_dimension(value_data_type="boolean")]}, None, "LAST"),
            ({"value_data_type": "string"}, None, "LAST"),
            ({}, [value_dimension(value_data_type="boolean")], "LAST"),
            ({}, None, "MEAN"),
        ],
    )
    def test_default_aggregation_method(
        self, metric_fields: dict[str, Any], shared: list[dict] | None, expected: str
    ) -> None:
        meta = multitsframe(metric("a", **metric_fields), value_dimensions_shared=shared)

        assert meta.default_aggregation_method("a") == expected
        assert meta.default_aggregation_methods() == {"a": expected}
        assert meta.default_aggregation_method("unknown") == "MEAN"

    def test_queried_interval(self) -> None:
        start, end = series({}).queried_interval()

        assert start == datetime.datetime(2026, 10, 18, tzinfo=datetime.UTC)
        assert end == datetime.datetime(2026, 10, 19, tzinfo=datetime.UTC)

    def test_no_queried_interval_for_discrete_datasets(self) -> None:
        meta = SeriesMetadata.model_validate(
            {
                "dataset_metadata": {
                    "metric_key": "id",
                    "queried_metrics": ["s"],
                    "single_metric": "s",
                    "ref_dataset_discrete": True,
                },
                "metrics": [metric("s")],
            }
        )

        assert meta.queried_interval() == (None, None)


class TestChangedVersions:
    def test_with_metric_shares_the_other_metrics(self) -> None:
        meta = multitsframe(metric("a"), metric("b"))

        changed = meta.with_metric("a", display_name="A")

        assert changed.display_name("a") == "A"
        assert meta.display_name("a") == "name of a"
        assert changed.metrics[1] is meta.metrics[1]
        assert changed.dataset_metadata is meta.dataset_metadata

    def test_with_metric_validates_the_changes(self) -> None:
        meta = multitsframe(metric("a"), metric("b"))

        with pytest.raises(ValidationError):
            meta.with_metric("a", name=5)
        with pytest.raises(MetadataConventionError, match="default_timezone"):
            meta.with_metric("a", default_timezone="Mars/Base")
        with pytest.raises(MetadataConventionError, match="more than once"):
            meta.with_metric("a", id="b")

    def test_with_metric_changing_the_id(self) -> None:
        changed = multitsframe(metric("a"), metric("b")).with_metric("a", id="c")

        assert changed.metric_ids() == ["c", "b"]

    def test_with_value_dimension(self) -> None:
        meta = series({"value_dimensions": [value_dimension(unit="m")]})

        changed = meta.with_value_dimension(None, "value", unit="cm")

        assert changed.unit() == "cm"
        assert meta.unit() == "m"
        with pytest.raises(KeyError):
            meta.with_value_dimension(None, "other", unit="cm")

    def test_with_dataset_metadata_checks_all_rules(self) -> None:
        meta = multitsframe(metric("a"))

        changed = meta.with_dataset_metadata(default_timezone="Europe/Berlin")

        assert changed.default_timezone("a") == "Europe/Berlin"
        assert changed.metrics is meta.metrics
        with pytest.raises(MetadataConventionError, match="ref_interval_start_timestamp"):
            meta.with_dataset_metadata(ref_interval_start_timestamp="2026-10-20T00:00:00Z")


class TestConversions:
    def test_narrowed_to_a_metric(self) -> None:
        meta = multitsframe(
            metric("a"), metric("b"), value_dimensions_shared=[value_dimension(unit="m")]
        )

        narrowed = meta.narrowed_to("b")

        assert isinstance(narrowed, SingleTSFrameMetadata)
        assert narrowed.metrics[0] is meta.metrics[1]
        assert narrowed.dataset_metadata.single_metric == "b"
        assert narrowed.dataset_metadata.queried_metrics == ("b",)
        assert narrowed.unit() == "m"
        with pytest.raises(KeyError):
            meta.narrowed_to("c")

    def singletsframe(self) -> SingleTSFrameMetadata:
        return SingleTSFrameMetadata.model_validate(
            {
                "dataset_metadata": dataset_metadata(single_metric="f", queried_metrics=["f"]),
                "metrics": [
                    metric(
                        "f",
                        value_dimensions=[
                            value_dimension("temperature", unit="°C"),
                            value_dimension("pressure", unit="bar"),
                        ],
                    )
                ],
                "value_dimensions_shared": [value_dimension("pressure", measurement="pressure")],
            }
        )

    def test_singletsframe_as_series(self) -> None:
        series_meta = self.singletsframe().as_series("pressure")

        assert isinstance(series_meta, SeriesMetadata)
        assert series_meta.units() == {"f": {"value": "bar"}}
        assert series_meta.measurement() == "pressure"
        with pytest.raises(KeyError):
            self.singletsframe().as_series("humidity")

    def test_series_as_singletsframe(self) -> None:
        series_meta = self.singletsframe().as_series("pressure")

        singletsframe_meta = series_meta.as_singletsframe("p")

        assert singletsframe_meta.units() == {"f": {"p": "bar", "value": None}}
        assert singletsframe_meta.measurement(column="p") == "pressure"

    def test_singletsframe_as_multitsframe(self) -> None:
        meta = self.singletsframe().as_multitsframe()

        assert isinstance(meta, MultiTSFrameMetadata)
        assert meta.metric_ids() == ["f"]
        assert meta.dataset_metadata.queried_metrics == ("f",)

    def test_singletsframe_as_multitsframe_with_another_id(self) -> None:
        meta = self.singletsframe().as_multitsframe("plant.f")

        assert meta.metric_ids() == ["plant.f"]
        assert meta.dataset_metadata.metric_key == "metric"
        assert meta.metric("plant.f").id == "f"
        assert meta.dataset_metadata.single_metric == "plant.f"

    def test_conversions_keep_extra_fields(self) -> None:
        extra = {"custom_root": {"source": "adapter"}}
        meta = SingleTSFrameMetadata.model_validate(self.singletsframe().model_dump() | extra)

        series_meta = meta.as_series("pressure")
        multitsframe_meta = meta.as_multitsframe()

        assert series_meta.model_extra == extra
        assert series_meta.as_singletsframe().model_extra == extra
        assert multitsframe_meta.model_extra == extra
        assert multitsframe_meta.narrowed_to("f").model_extra == extra


def test_enum_members_are_given_as_values() -> None:
    meta = series({"recording_mode": "irregular", "default_aggregation_method": "MAX"})

    assert type(meta.metric_info("recording_mode")) is str
    assert meta.metric_info("default_aggregation_method") == "MAX"
