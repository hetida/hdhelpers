"""Collection of useful functions to ease some operations in hetida designer code."""

from .locale import get_locale
from .timezone_handling import modify_timezone

__all__ = [
    "modify_timezone",
    "get_locale",
]
