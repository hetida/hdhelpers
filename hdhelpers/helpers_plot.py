import json
import logging
from datetime import datetime
from typing import Any

import pandas as pd
from pandas.tseries.frequencies import to_offset
from plotly.graph_objects import Figure  # type: ignore  # type: ignore
from pydantic import BaseModel, ValidationError

from hdhelpers.exceptions import HelperException, InsufficientPlottingData
from hdhelpers.helpers_time import estimate_plot_end, estimate_plot_start, modify_timezone
from hdhelpers.plot_target_settings import PlotTargetStyle, get_plot_target_settings
from hdhelpers.metadata import get_series_unit, get_series_display_name

logger = logging.getLogger("hdhelpers")


class PlottingSettings(BaseModel):
    hide_legend: bool = False
    hide_x_title: bool = False
    remove_plotly_bar: bool = False
    update_x_axes_tickformat: bool = False
    use_default_standoff: bool = False
    use_muplot_axes_color: bool = False
    use_muplot_grid: bool = False
    use_muplot_line_and_markers: bool = False
    use_platform_background: bool = False


platform_plotting_settings = PlottingSettings(
    hide_legend=True,
    hide_x_title=True,
    remove_plotly_bar=True,
    update_x_axes_tickformat=True,
    use_default_standoff=True,
    use_muplot_axes_color=True,
    use_muplot_grid=True,
    use_muplot_line_and_markers=True,
    use_platform_background=True,
)

default_plotting_settings = PlottingSettings()


# TODO: Klären warum das eine explonierte Funktion ist, wieso hängt sie nicht an
def get_perferred_colors() -> PlotTargetStyle:
    """Get thematically coherent colors for customizing plots

    Most color uses are already covered by the default settings of plotly_fig_to_json_dict().
    They are still included here in case coloring other plot elements in the same color is desired.
    Each color is given as a hex code, line_colors is a list of such, as specified in
    PlotTargetStyle.
    """
    plot_target_settings = get_plot_target_settings()

    return plot_target_settings.plot_target_style


def get_locale() -> str | None:
    """Get language for customizing text elements in plots

    Axis ticks are already covered by the default settings of plotly_fig_to_json_dict().
    The language of custom text elements should be adjusted to the locale.
    """
    plot_target_settings = get_plot_target_settings()

    return plot_target_settings.plot_target_locale


def _pad_to_timestamp(
    timestamp: pd.Timestamp, padding: str | None, add: bool = True
) -> pd.Timestamp:
    """Adds to  or subtracts from a given timestamp a given padding.

    Args:
        timestamp (pd.Timestamp): Timestamo to be modified.
        padding (str | None): Duration to be added or subtracted from timestamp. If it is None, the original timestamp is returned.
        add (bool, optional): Defines if duration is added to (True) or subtracted from (false) the timestamp. Defaults to True.

    Raises:
        HelperException: If given padding is not compatible with pandas.tseries.frequencies.to_offset().

    Returns:
        pd.Timestamp: Modified tiemstamp, usually used to define x-axis limits in a plot.
    """

    if padding is None:
        return timestamp

    try:
        if add is True:
            return timestamp + to_offset(padding)
        else:
            return timestamp - to_offset(padding)
    except ValueError as exc:
        raise HelperException(
            f"{padding} as padding value is an invalid duration, i.e. not a 'pandas frequency "
            "string'. Use something compatible with pandas.tseries.frequencies.to_offset()"
        ) from exc


# TODO: Namen
def get_and_pad_start_and_end_timestamp(
    series: pd.Series,
    timezone: str | None = None,
    start: datetime | str | None = None,
    start_padding: str | None = None,
    end: datetime | str | None = None,
    end_padding: str | None = None,
) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Get time period displayed on the x-axis

    Retrieves the start and end timestamps, prioritizing the explicit "start" and "end" parameters
    over the metadata of "series" and using the first and last index of the series if neither is
    given. If a padding is given, the respective timestamp is adjusted. That padding has to be
    formatted to be compatible with pandas.tseries.frequencies.to_offset().
    """
    # Get start and end
    start = estimate_plot_start(series, start)
    end = estimate_plot_end(series, end)

    if start is None:
        raise InsufficientPlottingData("No start timestamp found!")
    start_timestamp = start
    if end is None:
        raise InsufficientPlottingData("No end timestamp found!")
    end_timestamp = end

    # Convert timezone
    if timezone is not None:
        start_with_timezone = modify_timezone(start_timestamp, timezone)
        end_with_timezone = modify_timezone(end_timestamp, timezone)
    else:
        start_with_timezone = start_timestamp
        end_with_timezone = end_timestamp

    # Optionally add padding
    start_padded = _pad_to_timestamp(start_with_timezone, start_padding, add=False)
    end_padded = _pad_to_timestamp(end_with_timezone, end_padding, add=True)

    return start_padded, end_padded


def get_y_axis_label(series: pd.Series, default_title: str = "", default_unit: str = "") -> str:
    """Get full y-axis label from metadata

    Combines the title and unit provided by _get_display_name and _get_units.
    """

    unit = get_series_unit(series)
    title = get_series_display_name(series)

    if unit is None:
        logger.info("Metadata of series does not contain title. Using default unit")
        unit = default_unit

    if title is None:
        logger.info("Metadata of series does not contain display name. Using default title")
        title = default_title

    if len(unit) > 0:
        logger.debug("Unit is en empty string - returning only title")
        title = f"{title} [{unit}]"
    return title


def _serialize_plotly_fig(v: dict[str, Any] | Figure) -> Any:
    if isinstance(v, dict):
        return v

    # TODO: klären, was die comments bedeuten

    # possibly quite inefficient (multiple serialisation / deserialization) but
    # guarantees that the PlotlyJSONEncoder is used and so the resulting Json
    # should be definitely compatible with the plotly javascript library:

    # Whats the difference using json.loads(json.dumps(fig_dict_obj, cls=PlotlyJSONEncoder))
    # or employing fig.to_plotly_json()
    return json.loads(v.to_json())


def plotly_fig_to_json_dict(  # noqa: PLR0912, PLR0915
    fig: Figure,
    add_config_settings: bool = True,
    hide_legend: bool | None = None,
    hide_x_title: bool | None = None,
    remove_plotly_bar: bool | None = None,
    remove_plotly_icon: bool = True,
    update_x_axes_tickformat: bool | None = None,
    use_default_standoff: bool = False,
    use_minimum_margin: bool = True,
    use_muplot_axes_color: bool | None = None,
    use_muplot_grid: bool | None = None,
    use_muplot_line_and_markers: bool | None = None,
    use_platform_background: bool | None = None,
    use_platform_colorway: bool = True,
    use_platform_defaults: bool = True,
    use_simple_white_template: bool = True,
) -> Any:
    """Turn Plotly figure into a Python dict-like object

    This function can be used in visualization components to obtain the
    correct plotly json-like object from a Plotly Figure object.

    Additionally, this function has a dozen boolean parameters that can be
    set to standardize certain aspects of the plot styling in accordance
    with the hetida platform.

    See visualization components from the accompanying base components for
    examples on usage.
    """
    # TODO: Klären, hier kann ich sagen, das ich die platform default nutzen möchte, und dann
    # manuell noch einige Einstellungen anpassen. Die aktuelle Lösung wirkt nicht user-freundlich

    settings = default_plotting_settings
    if use_platform_defaults:
        settings = platform_plotting_settings

    # TODO: Klären, wieso einiges platform default sind und andere nicht, die aber danach klingen:
    # Remove plotly-bar, use_simple_white_template, use_default_standoff, use_platform_colorway
    #
    settings.hide_legend = hide_legend if hide_legend is not None else settings.hide_legend
    settings.hide_x_title = hide_x_title if hide_x_title is not None else settings.hide_x_title
    settings.remove_plotly_bar = (
        remove_plotly_bar if remove_plotly_bar is not None else settings.remove_plotly_bar
    )
    settings.update_x_axes_tickformat = (
        update_x_axes_tickformat
        if update_x_axes_tickformat is not None
        else settings.update_x_axes_tickformat
    )
    settings.use_default_standoff = (
        use_default_standoff if use_default_standoff is not None else settings.use_default_standoff
    )
    settings.use_muplot_axes_color = (
        use_muplot_axes_color
        if use_muplot_axes_color is not None
        else settings.use_muplot_axes_color
    )
    settings.use_muplot_grid = (
        use_muplot_grid if use_muplot_grid is not None else settings.use_muplot_grid
    )
    settings.use_muplot_line_and_markers = (
        use_muplot_line_and_markers
        if use_muplot_line_and_markers is not None
        else settings.use_muplot_line_and_markers
    )
    settings.use_platform_background = (
        use_platform_background
        if use_platform_background is not None
        else settings.use_platform_background
    )

    plot_target_settings = get_plot_target_settings()

    if use_platform_colorway:
        if plot_target_settings.plot_target_style.line_colors is None:
            logger.info("Cannot apply platform colorway as context does not deliver line_colors.")
        else:
            fig.update_layout(colorway=plot_target_settings.plot_target_style.line_colors)

    if use_simple_white_template:
        fig.update_layout({"template": "simple_white"})

    if settings.use_platform_background:
        if plot_target_settings.plot_target_style.background_color is None:
            logger.info("Cannot apply platform colorway as context does not deliver line_colors.")
        else:
            fig.update_layout(
                {
                    "paper_bgcolor": plot_target_settings.plot_target_style.background_color,
                    "plot_bgcolor": "rgba(0,0,0,0)",
                }
            )

    if settings.hide_legend:
        fig.update_layout(showlegend=False)

    if settings.hide_x_title:
        fig.update_xaxes(title_text="")

    if settings.update_x_axes_tickformat:
        if plot_target_settings.datetime_tick_format is None:
            logger.info(
                "Cannot apply update_x_axes_tickformat as context does not deliver datetime_tick_format."
            )
        else:
            fig.update_xaxes(tickformat=plot_target_settings.datetime_tick_format)

    if use_muplot_axes_color:
        if plot_target_settings.plot_target_style.axes_label_color is None:
            logger.info(
                "Cannot apply use_muplot_axes_color as context does not deliver axes_label_color."
            )
        else:
            fig.update_xaxes(color=plot_target_settings.plot_target_style.axes_label_color)
            fig.update_yaxes(color=plot_target_settings.plot_target_style.axes_label_color)

    if settings.use_default_standoff:
        fig.update_yaxes(title_standoff=5)

    if settings.use_muplot_line_and_markers:
        try:
            fig.update_traces(
                {
                    "marker": {"size": 3},
                    "line": {"width": 1},
                    "mode": "lines+markers",
                    "marker_symbol": "circle",
                }
            )
        except ValueError:
            logger.debug(
                msg="Skipping use_muplot_line_and_markers "
                "because this plot does not have compatible lines and markers"
            )

    if use_minimum_margin:
        fig.update_layout(
            {"margin": {"autoexpand": True, "l": 0, "r": 0, "b": 0, "t": 0, "pad": 0}}
        )

    if settings.use_muplot_grid:
        if plot_target_settings.plot_target_style.grid_color is None:
            logger.info("Cannot apply use_muplot_grid as context does not deliver grid_color.")
        else:
            grid_dict = {
                "showgrid": True,
                "gridcolor": plot_target_settings.plot_target_style.grid_color,
                "zeroline": True,
                "zerolinecolor": plot_target_settings.plot_target_style.grid_color,
            }
            fig.update_layout({"xaxis": grid_dict, "yaxis": grid_dict})

    fig_dict_obj = _serialize_plotly_fig(fig)

    if "config" not in fig_dict_obj:
        fig_dict_obj["config"] = {}

    if add_config_settings and plot_target_settings.plot_target_locale is not None:
        fig_dict_obj["config"]["locale"] = plot_target_settings.plot_target_locale

    if settings.remove_plotly_bar:
        fig_dict_obj["config"]["displayModeBar"] = False

    if remove_plotly_icon:
        fig_dict_obj["config"]["displaylogo"] = False

    # possibly quite inefficient (multiple serialisation / deserialization) but
    # guarantees that the PlotlyJSONEncoder is used and so the resulting Json
    # should be definitely compatible with the plotly javascript library:
    return fig_dict_obj
