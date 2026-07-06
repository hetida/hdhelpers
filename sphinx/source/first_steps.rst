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

    from hdhelpers.plotting import set_agnostic_theme, set_dt_ticks, resolve_color
    from hdhelpers.helpers import get_locale, modify_timezone
    from hdhelpers.metadata import get_queried_interval, get_series_name
    import plotly.graph_objects as go

    def main(*, series):
        # entrypoint function for this component
        # ***** DO NOT EDIT LINES ABOVE *****

        series = modify_timezone(series)

        fig = go.Figure([go.Scatter(x=series.index, y=series.values, marker={"color": resolve_color("ki.vision")})])

        start, end = get_queried_interval(series=series)
        fig.update_xaxes(range=(start, end))

        full_title = get_series_name(series=series, default_title="Level")
        fig.update_layout(yaxis_title=full_title)

        set_dt_ticks(fig)
        set_agnostic_theme(fig)

        return {"plot": fig}

