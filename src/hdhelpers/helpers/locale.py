import hdhelpers


def get_locale(explicit_locale: str | None = None) -> str | None:
    """Extract (Plotly) locale

    Infers Plotly locale from plot target settings or returns explicit provided
    locale.

    Args:
        explicit_locale (str | None): Defaults to None. Locale string like "de", "en-US" or similar. Will be returned instead of what is inferred from plot_target_settings if provided

    Returns:
        str | None:
            Extracted locale (like "de_DE")

    """
    if explicit_locale:
        return explicit_locale.replace("_", "-")

    plot_target_settings = hdhelpers.plot_target_settings.get_plot_target_settings()

    if plot_target_settings.plot_target_locale is not None:
        return plot_target_settings.plot_target_locale.replace("_", "-")

    return None
