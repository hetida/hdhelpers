"""Snapshot of the JSON Schemas of the metadata conventions

The hetida designer publishes these schemas in its openapi.json, so a change of the snapshot is a
change of the contract. To accept an intended change, run the tests with
UPDATE_SCHEMA_SNAPSHOT=1 and review the diff of the snapshot file.
"""

import json
import os
from pathlib import Path
from typing import Any

from pydantic.json_schema import models_json_schema

from hdhelpers.metadata.conventions import METADATA_MODELS

SNAPSHOT = Path(__file__).parent.parent / "data" / "convention_schemas.json"


def convention_schemas() -> dict[str, Any]:
    _, schemas = models_json_schema(
        [(model, "validation") for model in METADATA_MODELS.values()],
        ref_template="#/$defs/{model}",
    )
    return schemas


def test_json_schemas_match_snapshot() -> None:
    schemas = convention_schemas()
    if os.environ.get("UPDATE_SCHEMA_SNAPSHOT"):
        SNAPSHOT.write_text(
            json.dumps(schemas, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        )

    assert schemas == json.loads(SNAPSHOT.read_text())
