"""The models reject everything check_metadata_conventions reports as error"""

import copy
import datetime
from collections.abc import Callable
from typing import Any

import pandas as pd
import pytest
from pydantic import ValidationError

from hdhelpers.metadata.conventions import (
    METADATA_MODELS,
    MULTITSFRAME_METADATA_EXAMPLE,
    SERIES_METADATA_EXAMPLE,
    SINGLETSFRAME_METADATA_EXAMPLE,
    MetadataIssueSeverity,
    MetricMetadata,
    MultiTSFrameDatasetMetadata,
    MultiTSFrameMetadata,
    ValueDimensionMetadata,
    check_metadata_conventions,
)

EXAMPLES = {
    "SERIES": SERIES_METADATA_EXAMPLE,
    "SINGLETSFRAME": SINGLETSFRAME_METADATA_EXAMPLE,
    "MULTITSFRAME": MULTITSFRAME_METADATA_EXAMPLE,
}


def changed(data_type: str, change: Callable[[dict[str, Any]], Any]) -> dict[str, Any]:
    attrs = copy.deepcopy(EXAMPLES[data_type])
    change(attrs)
    return attrs


def first_metric(attrs: dict[str, Any]) -> dict[str, Any]:
    return attrs["metrics"][0]


def unhashable_metric_ids(attrs: dict[str, Any]) -> None:
    attrs["dataset_metadata"]["metric_key"] = "custom_key"
    for metric in attrs["metrics"]:
        metric["custom_key"] = [metric["external_id"]]


# (data type, change of its example, location of the error)
RULE_VIOLATIONS = [
    ("MULTITSFRAME", unhashable_metric_ids, "metrics[0]"),
    (
        "MULTITSFRAME",
        lambda a: first_metric(a).pop("external_id"),
        "metrics[0]",
    ),
    (
        "MULTITSFRAME",
        lambda a: a["metrics"][1].update(external_id=first_metric(a)["external_id"]),
        "metrics",
    ),
    (
        "MULTITSFRAME",
        lambda a: first_metric(a)["value_dimensions"].append(
            first_metric(a)["value_dimensions"][0]
        ),
        "metrics[0].value_dimensions",
    ),
    ("MULTITSFRAME", lambda a: first_metric(a).update(data_frequency="often"), None),
    ("MULTITSFRAME", lambda a: first_metric(a).update(data_frequency="-1h"), None),
    ("MULTITSFRAME", lambda a: first_metric(a).update(data_frequency_offset="5min"), None),
    (
        "MULTITSFRAME",
        lambda a: first_metric(a).update(data_frequency="1h", data_frequency_offset="2h"),
        None,
    ),
    ("MULTITSFRAME", lambda a: first_metric(a).update(default_timezone="Mars/Base"), None),
    ("MULTITSFRAME", lambda a: a["dataset_metadata"].update(default_timezone="CEST"), None),
    (
        "MULTITSFRAME",
        lambda a: first_metric(a).update(recording_mode="periodic"),
        "metrics[0].recording_mode",
    ),
    (
        "MULTITSFRAME",
        lambda a: first_metric(a).update(
            comments=[{"start_date": "2026-01-02T00:00:00Z", "end_date": "2026-01-01T00:00:00Z"}]
        ),
        None,
    ),
    (
        "MULTITSFRAME",
        lambda a: a["dataset_metadata"].update(only_invalidate=True, invalidate_dataset=False),
        "dataset_metadata.only_invalidate",
    ),
    (
        "MULTITSFRAME",
        lambda a: a["dataset_metadata"].pop("ref_interval_start_timestamp"),
        None,
    ),
    (
        "MULTITSFRAME",
        lambda a: a["dataset_metadata"].update(
            ref_interval_start_timestamp="2026-01-03T00:00:00+00:00"
        ),
        None,
    ),
    (
        "MULTITSFRAME",
        lambda a: a["dataset_metadata"].update(default_aggregation_interval="sometimes"),
        None,
    ),
    (
        "SINGLETSFRAME",
        lambda a: a["dataset_metadata"].update(single_metric="another metric"),
        "dataset_metadata.single_metric",
    ),
    (
        "SERIES",
        lambda a: first_metric(a)["value_dimensions"][0].update(column="other"),
        "metrics[0].value_dimensions",
    ),
]


@pytest.mark.parametrize(("data_type", "change", "location"), RULE_VIOLATIONS)
def test_models_reject_rule_violations(
    data_type: str, change: Callable[[dict[str, Any]], Any], location: str | None
) -> None:
    attrs = changed(data_type, change)
    errors = [
        issue
        for issue in check_metadata_conventions(attrs, data_type)  # type: ignore[arg-type]
        if issue.severity == MetadataIssueSeverity.ERROR
    ]
    assert len(errors) > 0
    if location is not None:
        assert location in [error.location for error in errors]

    with pytest.raises(ValidationError, match="Violates the metadata conventions") as raised:
        METADATA_MODELS[data_type].model_validate(attrs)
    assert errors[0].location in str(raised.value)


def test_warnings_do_not_make_metadata_invalid() -> None:
    attrs = changed(
        "MULTITSFRAME",
        lambda a: first_metric(a).update(channel_id="deprecated", unknown_field=1),
    )
    issues = check_metadata_conventions(attrs, "MULTITSFRAME")
    assert len(issues) > 0
    assert all(issue.severity == MetadataIssueSeverity.WARNING for issue in issues)

    MultiTSFrameMetadata.model_validate(attrs)


def nested_models(default_timezone: str) -> MultiTSFrameMetadata:
    return MultiTSFrameMetadata(
        dataset_metadata=MultiTSFrameDatasetMetadata.model_validate(
            MULTITSFRAME_METADATA_EXAMPLE["dataset_metadata"]
        ),
        metrics=(
            MetricMetadata(
                id="m1",
                external_id="plant_a.pressure",
                name="Pressure",
                default_timezone=default_timezone,
                value_dimensions=(
                    ValueDimensionMetadata(column="value", unit="bar", measurement=None),
                ),
            ),
        ),
    )


def test_rules_apply_to_nested_models() -> None:
    assert nested_models("UTC").metrics[0].default_timezone == "UTC"
    with pytest.raises(ValidationError, match=r"metrics\[0\].default_timezone"):
        nested_models("Mars/Base")


@pytest.mark.parametrize(
    "value",
    [
        datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
        datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone(datetime.timedelta(0))),
        pd.Timestamp("2026-01-01", tz="UTC"),
    ],
)
def test_timestamps_from_utc_datetimes(value: datetime.datetime) -> None:
    attrs = changed(
        "MULTITSFRAME", lambda a: a["dataset_metadata"].update(ref_interval_start_timestamp=value)
    )

    meta = MultiTSFrameMetadata.model_validate(attrs)

    assert meta.dataset_metadata.ref_interval_start_timestamp == "2026-01-01T00:00:00+00:00"


@pytest.mark.parametrize(
    ("value", "message_part"),
    [
        (datetime.datetime(2026, 1, 1), "naive"),  # noqa: DTZ001
        (pd.Timestamp("2026-01-01T01:00", tz="Europe/Berlin"), "not in UTC"),
    ],
)
def test_timestamps_from_other_datetimes_are_rejected(value: Any, message_part: str) -> None:
    attrs = changed(
        "MULTITSFRAME", lambda a: a["dataset_metadata"].update(ref_interval_start_timestamp=value)
    )

    with pytest.raises(ValidationError, match=message_part):
        MultiTSFrameMetadata.model_validate(attrs)


@pytest.mark.parametrize(
    "extra_value",
    [
        datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
        float("nan"),
        float("inf"),
        [1, float("nan")],
        {1: "integer key"},
        {"nested": {"value": object()}},
    ],
)
def test_extra_values_must_be_json(extra_value: Any) -> None:
    attrs = changed("MULTITSFRAME", lambda a: first_metric(a).update(extra=extra_value))

    with pytest.raises(ValidationError):
        MultiTSFrameMetadata.model_validate(attrs)


def test_deadband_must_be_finite() -> None:
    attrs = changed(
        "MULTITSFRAME",
        lambda a: first_metric(a)["value_dimensions"][0].update(deadband=float("inf")),
    )

    with pytest.raises(ValidationError, match="deadband"):
        MultiTSFrameMetadata.model_validate(attrs)
