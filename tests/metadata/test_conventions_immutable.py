import copy
import pickle
from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from hdhelpers.metadata.conventions import (
    METADATA_MODELS,
    MULTITSFRAME_METADATA_EXAMPLE,
    SERIES_METADATA_EXAMPLE,
    SINGLETSFRAME_METADATA_EXAMPLE,
    FrozenDict,
    MultiTSFrameMetadata,
)

EXAMPLES = {
    "SERIES": SERIES_METADATA_EXAMPLE,
    "SINGLETSFRAME": SINGLETSFRAME_METADATA_EXAMPLE,
    "MULTITSFRAME": MULTITSFRAME_METADATA_EXAMPLE,
}


def multitsframe_metadata(**metric_fields: Any) -> MultiTSFrameMetadata:
    attrs = copy.deepcopy(MULTITSFRAME_METADATA_EXAMPLE)
    attrs["metrics"][0] |= metric_fields
    return MultiTSFrameMetadata.model_validate(attrs)


@pytest.mark.parametrize("data_type", EXAMPLES)
def test_dump_reproduces_the_input(data_type: str) -> None:
    meta = METADATA_MODELS[data_type].model_validate(EXAMPLES[data_type])

    assert meta.model_dump(mode="json") == EXAMPLES[data_type]


def test_dump_leaves_out_optional_fields_with_none_or_default() -> None:
    attrs = copy.deepcopy(MULTITSFRAME_METADATA_EXAMPLE)
    attrs["dataset_metadata"] |= {"ref_dataset_discrete": False, "default_timezone": None}
    attrs["metrics"][0]["display_name"] = None
    attrs["metrics"][0]["value_dimensions"][0]["unit"] = None

    dumped = MultiTSFrameMetadata.model_validate(attrs).model_dump(mode="json")

    assert "ref_dataset_discrete" not in dumped["dataset_metadata"]
    assert "default_timezone" not in dumped["dataset_metadata"]
    assert "display_name" not in dumped["metrics"][0]
    # required, but nullable
    assert dumped["metrics"][0]["value_dimensions"][0]["unit"] is None


def test_dump_keeps_extra_fields_with_none() -> None:
    meta = multitsframe_metadata(anomaly_score=None)

    assert meta.model_dump(mode="json")["metrics"][0]["anomaly_score"] is None


def test_lists_become_tuples() -> None:
    meta = multitsframe_metadata(path=["site", "area"])

    assert isinstance(meta.metrics, tuple)
    assert isinstance(meta.metrics[0].value_dimensions, tuple)
    assert meta.metrics[0].path == ("site", "area")


def test_fields_cannot_be_changed() -> None:
    meta = multitsframe_metadata()

    with pytest.raises(ValidationError, match="frozen"):
        meta.metrics[0].name = "other"  # type: ignore[misc]


def test_extra_values_are_frozen() -> None:
    meta = multitsframe_metadata(
        inherited={"site": "Site A", "asset": {"type": "pump", "tags": ["a", "b"]}},
        anomaly_scores=[{"score": 0.5}],
    )
    inherited = meta.metrics[0].inherited
    assert inherited is not None
    asset = inherited.asset  # type: ignore[attr-defined]

    assert isinstance(asset, FrozenDict)
    assert isinstance(asset, Mapping)
    assert asset["tags"] == ("a", "b")
    assert meta.metrics[0].anomaly_scores == (FrozenDict(score=0.5),)  # type: ignore[attr-defined]
    with pytest.raises(TypeError, match="immutable"):
        asset["type"] = "valve"
    with pytest.raises(TypeError, match="immutable"):
        asset.update(type="valve")


@pytest.mark.parametrize("value", [True, 1, 1.5, "text", None])
def test_scalar_extra_values_are_kept(value: Any) -> None:
    meta = multitsframe_metadata(extra_value=value)

    assert meta.metrics[0].extra_value == value  # type: ignore[attr-defined]
    assert type(meta.metrics[0].extra_value) is type(value)  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    ("field", "value"), [("decimals", 1.0), ("decimals", "1"), ("deadband", "0.5")]
)
def test_numbers_are_not_coerced(field: str, value: Any) -> None:
    attrs = copy.deepcopy(MULTITSFRAME_METADATA_EXAMPLE)
    attrs["metrics"][0]["value_dimensions"][0][field] = value

    with pytest.raises(ValidationError):
        MultiTSFrameMetadata.model_validate(attrs)


def test_booleans_are_not_coerced() -> None:
    attrs = copy.deepcopy(MULTITSFRAME_METADATA_EXAMPLE)
    attrs["dataset_metadata"]["only_invalidate"] = "true"

    with pytest.raises(ValidationError):
        MultiTSFrameMetadata.model_validate(attrs)


def test_copies_are_the_original() -> None:
    meta = multitsframe_metadata(inherited={"asset": {"type": "pump"}})

    assert copy.deepcopy(meta) is meta
    assert copy.deepcopy(meta.metrics[0]) is meta.metrics[0]
    assert copy.deepcopy(meta.metrics[0].inherited.asset) is meta.metrics[0].inherited.asset  # type: ignore[union-attr]


def test_model_copy_never_changes_the_original() -> None:
    meta = multitsframe_metadata()

    changed = meta.model_copy(update={"metrics": meta.metrics[:1]}, deep=True)

    assert len(meta.metrics) == 2
    assert len(changed.metrics) == 1
    assert changed.metrics[0] is meta.metrics[0]


def test_pickle_round_trip() -> None:
    meta = multitsframe_metadata(inherited={"asset": {"tags": ["a"]}})

    unpickled = pickle.loads(pickle.dumps(meta))  # noqa: S301

    assert unpickled == meta
    assert isinstance(unpickled.metrics[0].inherited.asset, FrozenDict)


def test_pandas_operations_share_the_model() -> None:
    meta = multitsframe_metadata()
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=4, freq="h", tz="UTC"),
            "metric": ["plant_a.pressure", "plant_a.temperature"] * 2,
            "value": np.arange(4.0),
        }
    )
    df.attrs = {"hd_metadata": meta}

    derived = [
        df[df["value"] > 0],
        df.sort_values("value"),
        df.reset_index(drop=True),
        df["value"],
        df.copy(deep=False),
        df.copy(),
        pd.concat([df, df.copy()]),
    ]

    assert all(obj.attrs["hd_metadata"] is meta for obj in derived)
    assert all(obj.attrs is not df.attrs for obj in derived)
