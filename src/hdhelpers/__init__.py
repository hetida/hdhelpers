"""helper functions for writing components in hetida designer"""

from hdhelpers.helpers.color import FUSEKI_COLOR_CYCLE, resolve_color
from hdhelpers.helpers.locale import get_locale
from hdhelpers.helpers.plotly_theme import set_agnostic_theme
from hdhelpers.helpers.timestamp_ticks import set_dt_ticks

from . import exceptions, helpers, metadata
from .exceptions import HelperException, InsufficientPlottingData
from .plot_target_settings import StatusColors

# do not edit line of __version__ as it is automatically modified by running ./run build_package
__version__ = "0.0.4"

# function can be automated with from hdhelpers import *
__all__ = [
    "HelperException",
    "InsufficientPlottingData",
    "exceptions",
    "metadata",
    "helpers",
    "StatusColors",
    "get_locale",
    "resolve_color",
    "set_agnostic_theme",
    "set_dt_ticks",
    "FUSEKI_COLOR_CYCLE",
]
