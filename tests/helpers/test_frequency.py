"""Shared frequency parsing used by sampling and metadata validation."""

import pandas as pd
import pytest

from hdhelpers.helpers import frequency_duration, is_frequency, parse_fixed_frequency


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("15min", "15min"),
        ("D", "1D"),
        ("2D", "2D"),
        ("P1DT2H", "26h"),
        ("1 days 02:00:00", "26h"),
        (pd.Timedelta("500ms"), "500ms"),
    ],
)
def test_parse_fixed_frequency(value, expected):
    assert parse_fixed_frequency(value) == pd.Timedelta(expected)


@pytest.mark.parametrize("value", ["ME", "MS", "W"])
def test_calendar_frequencies_are_valid_but_have_no_fixed_duration(value):
    assert is_frequency(value)
    assert frequency_duration(value) is None
    with pytest.raises(ValueError, match="positive fixed duration"):
        parse_fixed_frequency(value)


@pytest.mark.parametrize("value", ["", "5", "invalid", "NaT", "nan"])
def test_invalid_frequency_strings(value):
    assert not is_frequency(value)
    assert frequency_duration(value) is None
    with pytest.raises(ValueError, match="positive fixed duration"):
        parse_fixed_frequency(value)


@pytest.mark.parametrize("value", ["0s", "-1min"])
def test_frequency_syntax_does_not_imply_positive_duration(value):
    assert is_frequency(value)
    assert frequency_duration(value) == pd.Timedelta(value)
    with pytest.raises(ValueError, match="positive fixed duration"):
        parse_fixed_frequency(value)


def test_zero_timedelta_is_rejected():
    with pytest.raises(ValueError, match="positive fixed duration"):
        parse_fixed_frequency(pd.Timedelta(0))


@pytest.mark.parametrize("value", [None, 60, True])
def test_fixed_frequency_requires_a_string_or_timedelta(value):
    with pytest.raises(TypeError, match="positive fixed duration"):
        parse_fixed_frequency(value)
