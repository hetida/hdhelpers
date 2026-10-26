"""helper functions for writing components in hetida designer"""

import importlib
from typing import TYPE_CHECKING, Any

from hdhelpers import exceptions, helpers, metadata
from hdhelpers.exceptions import HelperException, InsufficientPlottingData
from hdhelpers.helpers.locale import get_locale
from hdhelpers.helpers.timezone_handling import modify_timezone
from hdhelpers.plot_target_settings import StatusColors

if TYPE_CHECKING:
    from hdhelpers import plotting
    from hdhelpers.plotting.color import FUSEKI_COLOR_CYCLE, resolve_color
    from hdhelpers.plotting.plotly_theme import set_agnostic_theme
    from hdhelpers.plotting.timestamp_ticks import TICKFORMATSTOPS, set_dt_ticks

# do not edit line of __version__ as it is automatically modified by running ./run build_package
__version__ = "0.0.9"

# The plotting helpers need plotly, which comes with the optional extra hdhelpers[plotting]. They
# are imported on first access, so that everything else works without plotly.
_PLOTTING_ATTRIBUTES: dict[str, tuple[str, str | None]] = {
    "plotting": ("hdhelpers.plotting", None),
    "FUSEKI_COLOR_CYCLE": ("hdhelpers.plotting.color", "FUSEKI_COLOR_CYCLE"),
    "resolve_color": ("hdhelpers.plotting.color", "resolve_color"),
    "set_agnostic_theme": ("hdhelpers.plotting.plotly_theme", "set_agnostic_theme"),
    "TICKFORMATSTOPS": ("hdhelpers.plotting.timestamp_ticks", "TICKFORMATSTOPS"),
    "set_dt_ticks": ("hdhelpers.plotting.timestamp_ticks", "set_dt_ticks"),
}


def __getattr__(name: str) -> Any:
    if name not in _PLOTTING_ATTRIBUTES:
        raise AttributeError(f"module 'hdhelpers' has no attribute {name!r}")
    module_name, attribute = _PLOTTING_ATTRIBUTES[name]
    try:
        module = importlib.import_module(module_name)
    except ImportError as e:
        if (e.name or "").partition(".")[0] != "plotly":
            raise
        raise ImportError(
            f"hdhelpers.{name} needs plotly, which is installed with the extra hdhelpers[plotting]"
        ) from e
    value = module if attribute is None else getattr(module, attribute)
    globals()[name] = value
    return value


# import can be done by using `from hdhelpers import *``
__all__ = [
    "HelperException",
    "InsufficientPlottingData",
    "exceptions",
    "metadata",
    "plotting",
    "helpers",
    "StatusColors",
    "get_locale",
    "modify_timezone",
    "resolve_color",
    "set_agnostic_theme",
    "set_dt_ticks",
    "FUSEKI_COLOR_CYCLE",
    "TICKFORMATSTOPS",
]
