"""Collection of useful functions to ease some operations in hetida designer code."""

from .color import resolve_color
from .locale import get_locale
from .plotly_theme import set_agnostic_theme, theme_agnostic_template
from .timestamp_ticks import TICKFORMATSTOPS, set_dt_ticks
from .timezone_handling import modify_timezone

__all__ = [
    "modify_timezone",
    "resolve_color",
    "get_locale",
    "TICKFORMATSTOPS",
    "set_dt_ticks",
    "theme_agnostic_template",
    "set_agnostic_theme",
]
