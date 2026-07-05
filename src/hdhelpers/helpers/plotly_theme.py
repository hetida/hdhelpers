import plotly.graph_objects as go
import plotly.io as pio

NEUTRAL = "rgba(128,128,128,0.4)"
NEUTRAL_GRID = "rgba(128,128,128,0.25)"
NEUTRAL_TEXT = "rgba(128,128,128,0.9)"

theme_agnostic_template = go.layout.Template(
    layout=go.Layout(
        paper_bgcolor="rgba(0, 0, 0, 0)",
        plot_bgcolor="rgba(128, 128, 128, 0)",
        # plot_bg_color not 0,0,0,0 because zoom highlighting then does not work properly!
        # Must be >=128 to actuall work in light mode!
        font=dict(color=NEUTRAL_TEXT, family="Inter, Helvetica, sans-serif", size=12),
        xaxis=dict(
            showgrid=True,
            gridcolor=NEUTRAL_GRID,
            zerolinecolor=NEUTRAL,
            linecolor=NEUTRAL,
            tickfont=dict(color=NEUTRAL_TEXT),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor=NEUTRAL_GRID,
            zerolinecolor=NEUTRAL,
            linecolor=NEUTRAL,
            tickfont=dict(color=NEUTRAL_TEXT),
        ),
        hoverlabel=dict(
            bgcolor="rgba(128,128,128,0.85)",
            bordercolor="rgba(0,0,0,0.08)",
            font=dict(color="#fff", size=12, family="Inter, Helvetica, sans-serif"),
            namelength=0,
        ),
        modebar=dict(
            bgcolor="rgba(0,0,0,0)",
            color=NEUTRAL_TEXT,
            activecolor="rgba(128,128,128,1)",
        ),
    )
)

pio.templates["theme_agnostic"] = theme_agnostic_template

pio.templates.default = "theme_agnostic"


def set_agnostic_theme(fig: go.Figure) -> None:
    """Set Plotly template of figure to the theme_agnostic_template

    This Plotly template should yield good results for both light and dark themed
    backgrounds.

    Args:
        fig (plotly Figure object): Plotly figure object whose template will be set.

    Returns:
        None:
            Returns None, since the figure object is modified in place

    """
    fig.update_layout(template=theme_agnostic_template)
