"""Shared parsing of pandas frequencies and fixed UTC durations.

Calendar frequencies remain valid metadata frequencies, but cannot be used as fixed sampling
intervals. A day is interpreted as 24 hours in UTC, matching the metadata conventions.
"""

import re
from functools import lru_cache

import pandas as pd


@lru_cache(maxsize=1024)
def is_frequency(value: str) -> bool:
    """Whether value is a Pandas date offset alias or a timedelta string

    A unit is required, since e.g. "1" would be a timedelta string of 1 nanosecond.
    """
    if re.search("[A-Za-z]", value) is None:
        return False
    try:
        pd.tseries.frequencies.to_offset(value)
    except ValueError:
        try:
            # e.g. "nan" gives NaT
            return bool(pd.notna(pd.to_timedelta(value)))
        except ValueError:
            return False
    return True


@lru_cache(maxsize=1024)
def frequency_duration(value: str) -> pd.Timedelta | None:
    """Return a fixed UTC duration, or None for invalid or calendar-based frequencies.

    Numeric strings without a unit are invalid. Positivity is checked by parse_fixed_frequency,
    so valid zero and negative duration strings can still be inspected here.
    """
    if not is_frequency(value):
        return None
    try:
        offset = pd.tseries.frequencies.to_offset(value)
    except ValueError:
        try:
            # e.g. "P1D" or "1 days"
            duration = pd.to_timedelta(value)
        except ValueError:
            return None
        return None if pd.isna(duration) else duration
    if isinstance(offset, pd.offsets.Day):
        # a calendar day since pandas 3, i.e. 24 hours in UTC
        return pd.Timedelta(days=offset.n)
    if isinstance(offset, pd.offsets.Tick):
        return pd.Timedelta(offset)
    # calendar based, e.g. months
    return None


def parse_fixed_frequency(value: str | pd.Timedelta) -> pd.Timedelta:
    """Parse a positive fixed duration, rejecting calendar frequencies and bare numbers.

    Accept pandas aliases such as "15min" and "D", timedelta strings and Timedelta objects.
    Metadata may also contain calendar frequencies such as "MS"; these are not fixed durations.

    Raises:
        TypeError: value is neither a string nor a pandas Timedelta.
        ValueError: value has no unit, is invalid, calendar-based or not strictly positive.
    """
    message = "frequency must be a positive fixed duration such as '1min' or '1h'."
    if isinstance(value, pd.Timedelta):
        duration = value
    elif isinstance(value, str):
        duration = frequency_duration(value.strip())
    else:
        raise TypeError(message)
    if duration is None or duration <= pd.Timedelta(0):
        raise ValueError(message)
    return duration
