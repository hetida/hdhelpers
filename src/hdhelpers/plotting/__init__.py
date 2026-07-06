"""Collection of useful functions to ease plotting."""

from ..plotting.color import FUSEKI_COLOR_CYCLE, resolve_color
from ..plotting.plotly_theme import set_agnostic_theme, theme_agnostic_template
from ..plotting.timestamp_ticks import TICKFORMATSTOPS, set_dt_ticks

__all__ = [
    "resolve_color",
    "TICKFORMATSTOPS",
    "set_dt_ticks",
    "theme_agnostic_template",
    "set_agnostic_theme",
    "FUSEKI_COLOR_CYCLE",
]
