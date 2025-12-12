import json

import pytest
from pydantic import ValidationError

from hdhelpers.structure_metadata import MTSMetadata, SeriesMetadata


def test_interface_series_metadata():
    with open("tests/data/series_attrs.json", "r") as file:
        metadata_for_series = json.load(file)
    try:
        metadata = SeriesMetadata(**metadata_for_series)
    except ValidationError:
        pytest.fail("Unexpected MyError when initializing series metadata")

    assert metadata.get_unit() == {"value": "m³/s"}  # value
    assert metadata.get_display_name() == {"value": None}  # value
    assert metadata.get_name() == {"value": "Wasserstand Ruhr Meschede"}  # value
    assert metadata.get_start() == "2025-11-05T13:28:00Z"  # dataset_metadata
    assert metadata.get_end() == "2025-11-06T13:28:00Z"  # dataset_metadata


def test_interface_mts_metadata():
    with open("tests/data/mts_attrs.json", "r") as file:
        metadata_for_mts = json.load(file)

    try:
        metadata = MTSMetadata(**metadata_for_mts)
    except ValidationError:
        pytest.fail("Unexpected Error when initializing mts metadata")

    assert metadata.get_unit() == {"key1": "m³/s", "key2": "m³/h"}  # value
    assert metadata.get_display_name() == {"key1": None, "key2": None}  # value
    assert metadata.get_name() == {
        "key1": "Wasserstand Ruhr Meschede",
        "key2": "Wasserstand Ruhr Meschede (2)",
    }  # value
    assert metadata.get_start() == "2025-11-05T13:28:00Z"  # dataset_metadata
    assert metadata.get_end() == "2025-11-06T13:28:00Z"  # dataset_metadata
