#######################
First steps
#######################

How to get metadata with hdhelpers?
===================================

Let's say we want to retrieve the metadata of a timeseries.
In hetida designer this series can be represented as json for *direct provisioning*

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

We can retrieve the name and unit of the series with the following code

.. code-block:: python

    from hdhelpers.metadata import get_series_name, get_series_unit

    def main(*, series):
        # entrypoint function for this component
        # ***** DO NOT EDIT LINES ABOVE *****

        name = get_series_name(series)
        unit = get_series_unit(series)

        ...



How to use hdhelpers for plotting? (tbd)
========================================

Let's say we want to plot the same timeseries above using hdhelpers functionalities.
For example, we want to:
- plot the timeseries in a corresponding timezone,
- set the limits of the x-axis corresponding to the metadata,
- define the label of the y-axis corresponding to the metadata,
- and use standard colors for plotting.

Our component code might look like this to plot the timeseries accordingly:

.. code-block:: python

    from hdhelpers.plotting import get_and_pad_start_and_end_timestamp, get_y_axis_label, plotly_fig_to_json_dict
    from hdhelpers.helpers import modify_timezone
    import plotly.graph_objects as go

    def main(*, series):
        # entrypoint function for this component
        # ***** DO NOT EDIT LINES ABOVE *****

        series = modify_timezone(series)

        colors = get_colors_from_plot_target_settings()
        fig = go.Figure([go.Scatter(x=series.index, y=series.values, marker={"color": colors.status_colors.warn_color})])

        start, end = get_and_pad_start_and_end_timestamp(series=series, start_padding='5s')
        fig.update_xaxes(range=(start, end))

        full_title = get_y_axis_label(series=series, default_title="Level")
        fig.update_layout(yaxis_title=full_title)

        return {"plot": plotly_fig_to_json_dict(fig=fig)}

Explanation
-----------

- *modify_timezone*: We use `modify_timezone` function to set the timezone. Since our goal is just to make sure that the timestamps are timezone aware, not to convert it to a specific timezone, we do not pass a value for the `timezone` parameter. That way, if there is a `plot_target_timezone` set in the hetida designer's `plot_target_settings` context variable, that timezone will be used. Otherwise, the timestamps keep their current timezone or are converted to UTC if they are timezone naive.

- *get_colors_from_plot_target_settings*: To use a (global) standard color, we use `get_colors_from_plot_target_settings`, which returns the `plot_target_style` property of the `plot_target_settings` context variable. It contains a set of colors with specific purposes, such as `background_color`, and the `status_colors` object, which in turn contains the four status colors: `success_color`, `error_color`, `warn_color`, and `info_color`. The status colors have no hardwired use in a plot, but are intended to convey a message. In our example, we want to communicate that the order of magnitude of our data is potentially dangerous, so we use the `warn_color` for `fig`'s `marker["color"]` property, which determines the plot's marker and line color.

- *get_and_pad_start_and_end_timestamp*: We use `get_and_pad_start_and_end_timestamp` for precise control over the x-axis range. We do not set `start` and `end` explicitly because we want to parse them from the metadata, which reflects the chosen interval for which the data was requested. This way, we can see that there is missing data from 8:18 to 8:20. In the default behaviour of plotly this time range would not have been included possibly hiding missing data. Note: (1) We do not pass a `timezone` for the same reasons as with `modify_timezone`. (2) We also set a `start_padding`, so the markers of the first data point is not cut in half by the edge of the plot.

- *get_y_axis_label*: We use `get_y_axis_label` so our y-axis can be labeled by using information from the metadata. With the above input series, title and unit will be parsed from the metadata. In case the metadata does not contain the mentioned information, we provide a `default_title`, and `default_unit` to configure the axis label in such cases.

- *plotly_fig_to_json_dict*: We use `plotly_fig_to_json_dict` to apply standardized stylings and serialize the plotly figure into a json dict. All the standardized styling options are active by default, as detailed in [Styling Flags](#flags), so we do not have to set any for this example.
