import hdhelpers


def get_locale(explicit_locale: str | None = None) -> str | None:
    """Read the explicit locale or plot target locale, normalizing underscores to hyphens.

    Args:
        explicit_locale:
            Override locale, e.g. "de_DE". None or "" uses the plot target setting.

    Returns:
        str | None: Locale such as "de-DE", or None if no locale is configured.

    Code example:

    .. doctest::

        >>> get_locale("de_DE")         # returns "de-DE"
        'de-DE'

        >>> print(get_locale())         # returns locale from plot target settings of execution or None
        None
    """  # noqa: E501
    if explicit_locale:
        return explicit_locale.replace("_", "-")

    plot_target_settings = hdhelpers.plot_target_settings.get_plot_target_settings()

    if plot_target_settings.plot_target_locale is not None:
        return plot_target_settings.plot_target_locale.replace("_", "-")

    return None
