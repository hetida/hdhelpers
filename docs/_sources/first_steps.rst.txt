#######################
First steps
#######################

Example for plotting (tbd)
==========================

Let's say we want to plot a timeseries with data points.
In hetida designer this series can be represented as json for *direct provisioning* :

.. code-block:: json

    {
        "__hd_wrapped_data_object__":"SERIES",
        "__metadata__": {
            "single_metric_dataset_metadata": {
                "ref_interval_end_timestamp":"2020-01-01T08:20:00.000Z",
                "ref_interval_start_timestamp": "2020-01-01T08:10:00.000Z"
            },
            "single_metric_metadata": {
                "structured_metadata": {
                    "metric": {
                        "short_display_name": "Water Level",
                        "unit": "cm"
                    }
                }
            }
        },
        "__data__": {
            "2020-01-01T08:10:00+00:00": 1,
            "2020-01-01T08:15:00+00:00": 2,
            "2020-01-01T08:16:00+00:00": 3,
            "2020-01-01T08:17:00+00:00": 4,
        }
    }

Our component code might look like this:

.. code-block:: python

    from hdhelpers.plotting import get_and_pad_start_and_end_timestamp, get_y_axis_label, plotly_fig_to_json_dict
    from hdhelpers.helpers import modify_timezone
    import plotly.graph_objects as go

    def main(*, series):
        # entrypoint function for this component
        # ***** DO NOT EDIT LINES ABOVE *****
        # write your function code here.
        series = modify_timezone(series)

        colors = get_colors_from_plot_target_settings()
        fig = go.Figure([go.Scatter(x=series.index, y=series.values, marker={"color": colors.status_colors.warn_color})])

        start, end = get_and_pad_start_and_end_timestamp(series=series, start_padding='5s')
        fig.update_xaxes(range=(start, end))

        full_title = get_y_axis_label(series=series, default_title="Level")
        fig.update_layout(yaxis_title=full_title)

        return {"plot": plotly_fig_to_json_dict(fig=fig)}

First, we use *modify_timezone* to set the timezone. Since our goal is just to make sure that the timestamps are
timezone aware, not to convert it to a specific timezone, we do not pass a value for the `timezone` parameter. That way,
if there is a `plot_target_timezone` set in the hetida designer's `plot_target_settings` context variable, that timezone
will be used. Otherwise, the timestamps keep their current timezone or are converted to UTC if they are timezone naive.

With the timezone-corrected data in place, we turn it into a plotly Scatter Figure object called `fig`, that we can then
style to our liking. We want to customize said scatter plot by coloring the markers. To find a fitting color, we use
`get_colors_from_plot_target_settings`, which returns the `plot_target_style` property of the `plot_target_settings`
context variable. It contains a set of colors with specific purposes, such as `background_color`, and the
`status_colors` object, which in turn contains the four status colors: `success_color`, `error_color`, `warn_color`, and
`info_color`. The status colors have no hardwired use in a plot, but are intended to convey a message. In our example,
we want to communicate that the order of magnitude of our data is potentially dangerous, so we use the `warn_color` for
`fig`'s `marker["color"]` property, which determines the plot's marker and line color.

Now, we use `get_and_pad_start_and_end_timestamp` for precise control over the x-axis range. We do not set `start` and
`end` explicitly because we want to parse them from the series metadata, which reflects the chosen interval for which
plotting data was requested. This way, we can see that there is missing data from 8:18 to 8:20, where normally Plotly
would not have included that time range in the plot. We do not pass a `timezone` for the same reasons as with
`modify_timezone`. We also set a `start_padding`, so the markers of the first data point is not cut in half by the edge
of the plot. With start and end parsed, we can update `fig`'s x-axis range.

Next, we use `get_y_axis_label` so our y-axis can be labeled with the series metadata. With the above input series,
title and unit will be parsed from the series metadata, but in case the component is ever run without series metadata,
we provide a `default_title`, but we leave the `default_unit` at its empty default value. Then, we update `fig` with our
title.

Lastly, we use `plotly_fig_to_json_dict` to apply standardized stylings and serialize the plotly figure into a json
dict. All the standardized styling options are active by default, as detailed in [Styling Flags](#flags), so we do not
have to set any for this example.

As a result we get the following plot:

Further Explanation
===================

* `use_platform_defaults=True` sets the following flags to `True`, which are by default `False`:
* `hide_legend` sets the plotly layout parameter `showlegend=False` to hide the plot's legend
* `hide_x_title` sets the plotly xaxes parameter `title_text=''` to hide the x-axis title
* `remove_plotly_bar` sets the plotly figure's `displayModeBar` setting to `False` to remove the plotly bar from the plot
* `update_x_axes_tickformat` sets the plotly xaxes parameter `tickformat` to the `datetime_tick_format` property the hetida platform writes into the hetida designer's `plot_target_settings` context variable (unless the property is `None`)
* `use_default_standoff` sets the plotly yaxes parameter `title_standoff=5`
* `use_muplot_axes_color` sets the plotly xaxes and yaxes parameter `color` to the `axes_label_color` property the hetida platform writes into the hetida designer's `plot_target_settings` context variable (unless the property is `None`)
* `use_muplot_grid` makes the plotly grid visible and colors it in according to the `grid_color` property the hetida platform writes into the hetida designer's `plot_target_settings` context variable (unless the property is `None`)
* `use_muplot_line_and_markers` sets the plotly traces to the following style, which matches the hetida platform's µplots:

.. code-block:: json

    {
        "marker": {"size": 3},
        "line": {"width": 1},
        "mode": "lines+markers",
        "marker_symbol": "circle",
    }

* `use_platform_background` sets the plotly layout parameter `paper_bgcolor` to the `background_color` property the
  hetida platform writes into the hetida designer's `plot_target_settings` context variable (unless the property is
  `None`) and it sets `plot_bgcolor=rgba(0,0,0,0)` so the "paper background" is visible through the "plot background"
* `plotly_fig_to_json_dict` has four more boolean parameters:
    * `add_config_settings` sets the plotly figure's locale to
      the `plot_target_locale` property the hetida platform writes into the hetida designer's `plot_target_settings` context
      variable (unless the property is `None`)
    * `remove_plotly_icon` sets the plotly figure's `displaylogo` setting to
      `False` to remove the plotly logo from the plot
    * `use_minimum_margin` sets the plotly layout parameter
      `margin={"autoexpand": True, "l": 0, "r": 0, "b": 0, "t": 0, "pad": 0}` to minimize the plot's margins
    * `use_platform_colorway` sets the plotly layout parameter `colorway` to the `line_colors` property the hetida platform
      writes into the hetida designer's `plot_target_settings` context variable (unless the property is `None`). Note that in
      Plotly, explicitly set line colors have higher priority than those in the colorway, so setting this parameter to `False`
      is rarely necessary. * `use_simple_white_template` sets the plotly layout parameter `template=simple_white`
