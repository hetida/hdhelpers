"""Timings of the metadata models for MULTITSFRAMEs with many metrics, against the budget

Not part of the test run. Run with: uv run python tests/benchmarks/benchmark_metadata.py [metrics]
"""

import copy
import sys
import timeit
from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd

from hdhelpers.metadata import META_KEY, attach_metadata, attrs_to_json, get_units
from hdhelpers.metadata.conventions import MultiTSFrameMetadata

# milliseconds per 1000 metrics, for metadata with nested extra fields, recording information and
# comments as below, unless independent of the number of metrics (FIXED)
BUDGET = {
    "parse (model_validate incl. rules)": 12.0,
    "deepcopy(attrs) with attached model": 0.01,
    "filter -> sort -> reset_index": 1.0,
    "with_metric": 0.5,
    "attrs_to_json": 6.0,
    "get_units": 5.0,
}
# pandas shares the attached model instead of copying it
FIXED = {"deepcopy(attrs) with attached model", "filter -> sort -> reset_index"}


def attrs_of(metric_count: int) -> dict[str, Any]:
    metrics = []
    for index in range(metric_count):
        metric: dict[str, Any] = {
            "id": f"00000000-0000-4000-8000-{index:012d}",
            "external_id": f"plant.m{index}",
            "name": f"Metric {index}",
            "path": ["site", "area", f"unit{index % 10}"],
            "value_dimensions": [{"column": "value", "unit": "bar", "measurement": "pressure"}],
            "inherited": {"site": "Site A", "asset": {"type": "pump", "tags": ["a", "b"]}},
            "recording_mode": "periodic",
            "data_frequency": "1h",
            "default_timezone": "Europe/Berlin",
        }
        if index % 10 == 0:
            metric["comments"] = [
                {"content": "checked", "username": "x", "created_at": "2026-01-01T00:00:00Z"}
            ]
        metrics.append(metric)
    return {
        "dataset_metadata": {
            "metric_key": "external_id",
            "queried_metrics": [f"plant.m{index}" for index in range(metric_count)],
            "ref_interval_start_timestamp": "2026-01-01T00:00:00+00:00",
            "ref_interval_end_timestamp": "2026-01-02T00:00:00+00:00",
            "ref_interval_type": "closed",
        },
        "metrics": metrics,
    }


def milliseconds(function: Callable[[], Any], number: int = 20) -> float:
    return min(timeit.repeat(function, number=number, repeat=5)) / number * 1e3


def main(metric_count: int) -> None:
    attrs = attrs_of(metric_count)
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=100, freq="h", tz="UTC"),
            "metric": "plant.m1",
            "value": np.arange(100.0),
        }
    )
    frame.attrs = copy.deepcopy(attrs)
    meta = attach_metadata(frame)
    assert isinstance(frame.attrs[META_KEY], MultiTSFrameMetadata)
    assert meta is not None

    timings = {
        "parse (model_validate incl. rules)": milliseconds(
            lambda: MultiTSFrameMetadata.model_validate(attrs), 5
        ),
        "deepcopy(attrs) with attached model": milliseconds(
            lambda: copy.deepcopy(frame.attrs), 1000
        ),
        "filter -> sort -> reset_index": milliseconds(
            lambda: frame[frame["value"] > 10].sort_values("value").reset_index(drop=True)
        ),
        "with_metric": milliseconds(lambda: meta.with_metric("plant.m1", display_name="M1")),
        "attrs_to_json": milliseconds(lambda: attrs_to_json(frame.attrs), 5),
        "get_units": milliseconds(lambda: get_units(frame), 5),
    }
    scale = metric_count / 1000
    print(f"{metric_count} metrics, pandas {pd.__version__}")
    for name, value in timings.items():
        budget = BUDGET[name] * (1 if name in FIXED else scale)
        status = "ok" if value <= budget else "OVER BUDGET"
        print(f"  {name:40s} {value:9.3f} ms  (budget {budget:7.3f} ms)  {status}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1000)
