import copy
import json
from typing import Any

import numpy as np
import pandas as pd
import pytest

from hdhelpers.metadata import (
    META_KEY,
    MetadataConventionError,
    attach_metadata,
    attrs_to_json,
    check_metadata_conventions,
    read_metadata,
    set_metadata,
)
from hdhelpers.metadata.attached import infer_data_type
from hdhelpers.metadata.conventions import (
    MULTITSFRAME_METADATA_EXAMPLE,
    SINGLETSFRAME_METADATA_EXAMPLE,
    MultiTSFrameMetadata,
    SingleTSFrameMetadata,
)

OTHER_ATTRS = {"hetida-designer_filters": {"from": "2026-01-01"}}


def multitsframe(attrs: dict[str, Any] | None = None) -> pd.DataFrame:
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01T06:00", periods=4, freq="h", tz="UTC"),
            "metric": ["plant_a.pressure", "plant_a.temperature"] * 2,
            "value": np.arange(4.0),
        }
    )
    df.attrs = copy.deepcopy(
        MULTITSFRAME_METADATA_EXAMPLE | OTHER_ATTRS if attrs is None else attrs
    )
    return df


def singletsframe() -> pd.DataFrame:
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01T06:00", periods=2, freq="h", tz="UTC"),
            "value": [1.0, 2.0],
        }
    )
    df.attrs = copy.deepcopy(SINGLETSFRAME_METADATA_EXAMPLE)
    return df


def test_infer_data_type() -> None:
    assert infer_data_type(pd.Series([1.0])) == "SERIES"
    assert infer_data_type(multitsframe()) == "MULTITSFRAME"
    assert infer_data_type(singletsframe()) == "SINGLETSFRAME"


class TestAttach:
    def test_model_replaces_the_convention_keys(self) -> None:
        df = multitsframe()

        meta = attach_metadata(df)

        assert isinstance(meta, MultiTSFrameMetadata)
        assert df.attrs == OTHER_ATTRS | {META_KEY: meta}

    def test_attached_model_stays(self) -> None:
        df = multitsframe()
        meta = attach_metadata(df)

        assert attach_metadata(df) is meta

    @pytest.mark.parametrize(
        "attrs",
        [
            {},
            OTHER_ATTRS,
            {"metrics": []},
            MULTITSFRAME_METADATA_EXAMPLE | {"dataset_metadata": {"metric_key": "id"}},
        ],
    )
    def test_attrs_without_valid_metadata_stay(self, attrs: dict[str, Any]) -> None:
        df = multitsframe(attrs)

        assert attach_metadata(df) is None
        assert df.attrs == attrs


class TestRead:
    def test_attached_model(self) -> None:
        df = multitsframe()
        meta = attach_metadata(df)

        assert read_metadata(df) is meta
        assert read_metadata(df, "MULTITSFRAME") is meta
        assert read_metadata(df[df["value"] > 1]) is meta

    def test_metadata_of_another_data_type(self) -> None:
        df = singletsframe()
        meta = attach_metadata(df)
        series = df["value"]

        assert read_metadata(series) is meta
        assert read_metadata(series, "SERIES") is None
        with pytest.raises(MetadataConventionError, match="SINGLETSFRAME metadata"):
            read_metadata(series, "SERIES", required=True)

    def test_plain_attrs_are_parsed_without_attaching(self) -> None:
        df = singletsframe()

        meta = read_metadata(df)

        assert isinstance(meta, SingleTSFrameMetadata)
        assert df.attrs == SINGLETSFRAME_METADATA_EXAMPLE

    def test_no_metadata(self) -> None:
        df = multitsframe(OTHER_ATTRS)

        assert read_metadata(df) is None
        with pytest.raises(MetadataConventionError, match="No metadata"):
            read_metadata(df, required=True)

    def test_invalid_metadata(self) -> None:
        attrs = copy.deepcopy(MULTITSFRAME_METADATA_EXAMPLE)
        attrs["metrics"][0]["default_timezone"] = "Mars/Base"
        df = multitsframe(attrs)

        assert read_metadata(df) is None
        with pytest.raises(MetadataConventionError) as raised:
            read_metadata(df, required=True)
        assert [issue.location for issue in raised.value.issues] == ["metrics[0].default_timezone"]


def test_set_metadata_replaces_attached_metadata_and_convention_keys() -> None:
    df = multitsframe()
    meta = MultiTSFrameMetadata.model_validate(MULTITSFRAME_METADATA_EXAMPLE)

    set_metadata(df, meta)

    assert df.attrs == OTHER_ATTRS | {META_KEY: meta}


def test_attrs_to_json_reproduces_the_attrs() -> None:
    df = multitsframe()
    attach_metadata(df)

    assert attrs_to_json(df.attrs) == MULTITSFRAME_METADATA_EXAMPLE | OTHER_ATTRS
    assert json.loads(json.dumps(attrs_to_json(df.attrs))) == attrs_to_json(df.attrs)
    assert attrs_to_json(OTHER_ATTRS) == OTHER_ATTRS


def test_check_metadata_conventions_with_attached_metadata() -> None:
    df = multitsframe()
    issues = check_metadata_conventions(df)
    attach_metadata(df)

    assert check_metadata_conventions(df) == issues
