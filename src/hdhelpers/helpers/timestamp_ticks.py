"""Language agnostic multi-zoom-level x axis time range ticks for plotly

Usage:

    fig.update_xaxes(
        tickformatstops=TICKFORMATSTOPS
    )
"""

import plotly.graph_objects as go

TICKFORMATSTOPS = [
    # language agnostic, isoformat inspired, plotl x axis timestamp formatting
    # defined for multiple zoom levels
    # always showing a tick with the current day somewhere for reference
    dict(dtickrange=[None, 1000], value="%H:%M:%S.%L\n%Y-%m-%d"),
    dict(dtickrange=[1000, 60000], value="%H:%M:%S\n%Y-%m-%d"),
    dict(dtickrange=[60000, 3600000], value="%H:%M\n%Y-%m-%d"),
    dict(dtickrange=[3600000, 86400000], value="%H:%M\n%Y-%m-%d"),
    dict(dtickrange=[86400000, 604800000], value="%m-%d"),
    dict(dtickrange=[604800000, "M1"], value="%m-%d"),
    dict(dtickrange=["M1", "M12"], value="%Y-%m"),
    dict(dtickrange=["M12", None], value="%Y"),
]


def set_dt_ticks(fig: go.Figure) -> None:
    """Set x datetime tick labels to language agnostic format

    Sets the x axes tick format of the Plotly Figure to some isoformat inspired
    timestamp format, adequately for multiple zoom levels.

    Infers Plotly locale from plot target settings or returns explicit provided
    locale.

    Args:
        fig (plotly Figure object): Plotly figure object whose x axes will be modified.

    Returns:
        None:
            Returns None, since the figure object is modified in place

    """
    fig.update_xaxes(tickformatstops=TICKFORMATSTOPS)
