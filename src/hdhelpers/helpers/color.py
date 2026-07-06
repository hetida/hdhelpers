FUSEKI_COLORS = {
    "ki.vision": "#eb7c45",  # orange
    "ki.change": "#2fae53",  # green
    "ki.contrast": "#232326",  # black
    "ki.insight": "#e5cf64",  # yellow / gold
    "ki.tech": "#80b0ec",  # blue
    "ki.shade": "#8c8c98",  # gray
    "ki.vision.bright": "#ffb058",  # light orange
    "ki.change.bright": "#89ce6e",  # light green
    "ki.light": "#f8f8f8",  # off-white / light gray
    "ki.energy": "#eb6962",  # red / coral
    "ki.science": "#bd7abb",  # purple
    # more telling color names:
    "ki.orange": "#eb7c45",  # orange
    "ki.green": "#2fae53",  # green
    "ki.black": "#232326",  # black
    "ki.yellow": "#e5cf64",  # yellow / gold
    "ki.blue": "#80b0ec",  # blue
    "ki.gray": "#8c8c98",  # gray
    "ki.lightyellow": "#ffb058",  # light orange
    "ki.lightorange": "#ffb058",  # light orange
    "ki.lightgreen": "#89ce6e",  # light green
    "ki.white": "#f8f8f8",  # off-white / light gray
    "ki.red": "#eb6962",  # red / coral
    "ki.purple": "#bd7abb",  # purple
}


def resolve_color(color_str: str) -> str:
    """Resolves Fuseki Colors and returns resulting color string

    Non-fuseki (color) strings are returned just as they are.

    Args:
        color_str (str): Color string like "#ea1255", "orange" or "ki.shade" (Fuseki color)

    Returns:
        str:
            Returns the resolved color string.


    Code example:

    .. doctest::

        >>> resolve_color("red")
        'red'
        >>> resolve_color("ki.energy")
        '#eb6962'
    """
    return FUSEKI_COLORS.get(color_str, color_str)
