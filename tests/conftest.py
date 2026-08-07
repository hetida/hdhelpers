import json

import pandas as pd
import pytest

from .data.fixtures.helpers import dataframe, multicolumn_frame, series_summer, series_winter
from .data.fixtures.metadata import (
    empty_mts_with_attr,
    empty_mts_with_old_attr,
    empty_mts_with_old_attr_real,
    empty_series_with_attr,
    empty_series_with_old_attr,
    empty_series_with_old_attr_real,
    empty_singletsframe_with_attr,
)
