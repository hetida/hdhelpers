from copy import deepcopy

import pandas as pd

from hdhelpers import metadata as md
from hdhelpers.metadata.conventions import (
    MULTITSFRAME_METADATA_EXAMPLE,
    SERIES_METADATA_EXAMPLE,
    SINGLETSFRAME_METADATA_EXAMPLE,
)

timestamps = pd.to_datetime(["2026-01-01T00:00:00Z", "2026-01-01T00:15:00Z"])

# SERIES: one metric, with timestamps in the index; values are in metres.
series = pd.Series([1.0, 1.2], index=timestamps, name="level")
series.attrs = deepcopy(SERIES_METADATA_EXAMPLE)

# SINGLETSFRAME: one metric with several value columns; "value" is in degrees Celsius.
dataframe = pd.DataFrame(
    {"timestamp": timestamps, "value": [20.0, 21.0], "state": ["valid", "valid"]}
)
dataframe.attrs = deepcopy(SINGLETSFRAME_METADATA_EXAMPLE)

# MULTITSFRAME: several metrics, identified by the "metric" column.
multitsframe = pd.DataFrame(
    {
        "timestamp": timestamps,
        "metric": ["plant_a.pressure", "plant_a.temperature"],
        "value": [1.0, 20.0],
    }
)
multitsframe.attrs = deepcopy(MULTITSFRAME_METADATA_EXAMPLE)
