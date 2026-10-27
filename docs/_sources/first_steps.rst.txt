#######################
First steps
#######################

How to get metadata with hdhelpers?
===================================

Let's say we want to retrieve the metadata of a timeseries, which follows the
`hetida designer metadata conventions`_.
In hetida designer this series can be represented as json for *direct provisioning*

.. code-block:: json

    {
        "__hd_wrapped_data_object__": "SERIES",
        "__metadata__": {
            "dataset_metadata": {
                "metric_key": "external_id",
                "single_metric": "water.north.level",
                "ref_interval_start_timestamp": "2020-01-01T08:10:00+00:00",
                "ref_interval_end_timestamp": "2020-01-01T08:20:00+00:00",
                "ref_interval_type": "closed"
            },
            "metrics": [
                {
                    "external_id": "water.north.level",
                    "name": "Water level north",
                    "short_display_name": "Water Level",
                    "value_dimensions": [{"column": "value", "unit": "cm"}],
                    "inherited": {"latitude": 51.43, "longitude": 7.58}
                }
            ]
        },
        "__data__": {
            "2020-01-01T08:10:00+00:00": 1,
            "2020-01-01T08:15:00+00:00": 2,
            "2020-01-01T08:16:00+00:00": 3,
            "2020-01-01T08:17:00+00:00": 4
        }
    }

We can retrieve the name, unit and latitude of the series with the following code

.. code-block:: python

    from hdhelpers.metadata import get_series_info, get_series_name, get_series_unit

    def main(*, series):
        # entrypoint function for this component
        # ***** DO NOT EDIT LINES ABOVE *****

        name = get_series_name(series)  # "Water level north"
        unit = get_series_unit(series)  # "cm"
        latitude = get_series_info(series, "latitude")  # 51.43, inherited from the hierarchy

        ...

.. _hetida designer metadata conventions: https://hetida.github.io/hetida-designer/user_guide/attached_metadata/

Where does the information come from?
=====================================

The metadata conventions allow to provide information on different levels. The functions
look for it in the following order and use the first information which is not null. Information
provided as null counts as missing.

**Dedicated information** like the unit, name, display name, short display name and measurement
(e.g. ``get_units``, ``get_series_unit``, ``get_singlets_units``) is looked up per value dimension:

1. in the value dimension itself,
2. only for the value dimension ``"value"``: in the metric,
3. in ``"value_dimensions_shared"``.

For (short) display names, each field is looked up on all of these levels before falling back to
the next field: short display name, then display name, then name. So e.g. a display name provided
for the metric wins over the name of its value dimension.

**Other information** is looked up by ``get_metric_info`` and ``get_singlets_metric_info``

1. in the metric itself,
2. in its value dimension ``"value"``,
3. in ``"value_dimensions_shared"``,
4. in the properties the metric inherits from objects higher up in an asset hierarchy (given under
   ``"inherited"`` in the metric metadata), e.g. the latitude of the plant a sensor belongs to.

``get_series_info`` and ``get_singlets_info`` use the order of the dedicated information, followed
by the inherited properties as last resort.

The inherited properties can be switched off via the keyword argument ``include_inherited=False``.
In contrast, the functions for dedicated information do not use them by default, since an
inherited property with the same label usually does not describe the metric itself, e.g. a
property "unit" of a plant. Pass ``include_inherited=True`` to use them as last resort anyway.

Entries which do not adhere to the conventions are skipped: metrics which are no objects or
whose field named by the metric key is no string, and value dimensions which are no objects or
whose column is no string. ``"value_dimensions"`` and ``"value_dimensions_shared"`` which are no
lists count as empty, a metric key which is no string as missing, i.e. ``"id"`` is used.

How to query nested information?
================================

The information requested from ``get_metric_info``, ``get_singlets_metric_info``,
``get_series_info`` and ``get_singlets_info`` is interpreted as a `glom`_ spec. A string is a
path in which dots separate the keys, so it also reaches into sub dictionaries. Let's say the
metric of the series above additionally provides comments and information on its sensor (the
conventions allow additional fields at every level), and the label of one of its inherited
properties contains a dot:

.. code-block:: json

    {
        "external_id": "water.north.level",
        "name": "Water level north",
        "sensor": {
            "manufacturer": "Acme",
            "calibration": {"date": "2026-03-01", "offset": 0.02}
        },
        "comments": [
            {"content": "Gauge maintenance"},
            {"content": "Sensor replaced"}
        ],
        "value_dimensions": [{"column": "value", "unit": "cm"}],
        "inherited": {"latitude": 51.43, "operator.name": "Ruhrverband"}
    }

We can retrieve the nested information with the following code

.. code-block:: python

    from glom import Path
    from hdhelpers.metadata import get_series_info

    def main(*, series):
        # entrypoint function for this component
        # ***** DO NOT EDIT LINES ABOVE *****

        manufacturer = get_series_info(series, "sensor.manufacturer")  # "Acme"
        calibration_date = get_series_info(series, "sensor.calibration.date")  # "2026-03-01"
        latitude = get_series_info(series, "inherited.latitude")  # 51.43, never the metric's own
        firmware = get_series_info(series, "sensor.firmware")  # None, not provided

        # any other glom spec, e.g. the content of each comment
        comments = get_series_info(series, ("comments", ["content"]))
        # ["Gauge maintenance", "Sensor replaced"]

        # a key which itself contains dots requires a glom Path
        operator = get_series_info(series, Path("operator.name"))  # "Ruhrverband"

        ...

For a MULTITSFRAME, ``get_metric_info(multitsframe, "sensor.manufacturer")`` provides the
manufacturer keyed by metric accordingly.

The fallbacks described above apply to the whole path, e.g. ``"sensor.manufacturer"`` is looked
up in the metric first, then in its value dimension ``"value"`` and so on. A path which is not
present yields None instead of an error. Note that a plain string like ``"operator.name"`` is
always split at its dots, so it does not find the inherited property ``"operator.name"``.

A spec may also transform the information, e.g. ``("name", str.upper)``. Since information
provided as null counts as missing, such a spec may receive null: on the metric itself and, if
the metric does not provide the information, on the levels it falls back to. Errors raised by
the spec are not caught. So either let it handle None, or rather transform the information
after retrieving it.

.. _glom: https://glom.readthedocs.io/

Which time zone to compute in?
==============================

Metadata may provide a ``default_timezone`` for each metric and for the dataset metadata: the
time zone the timeseries should be evaluated in by default. It belongs to the data, e.g. it is
the time zone of the plant a sensor belongs to, and it is meant for **computations**:
Components evaluating timeseries in calendar intervals should respect it. E.g. a component
aggregating daily values should bucket the days from midnight to midnight of this time zone,
so its results depend on it.

It is **not** meant for displaying timestamps. That is what the time zone of the plot target
settings is for, which the hetida platform provides for the view, e.g. the time zone of a
dashboard or of the user looking at a plot. ``modify_timezone`` uses it if no ``to_timezone``
is given. Both may differ: A report on a plant in Germany may aggregate days in
``"Europe/Berlin"`` and nevertheless show its timestamps to a viewer in New York in
``"America/New_York"``.

``get_series_default_timezone``, ``get_singlets_default_timezone`` and
``get_default_timezones`` (keyed by metric) provide the default time zone of a metric. If the
metric does not provide one, they fall back to the one of the dataset metadata, which applies
to all metrics without their own. If neither provides one, they return None. The time zone is
an IANA time zone name like ``"Europe/Berlin"``, which respects daylight saving time, or a
fixed UTC offset like ``"+02:00"``. pandas accepts both.

.. code-block:: python

    from hdhelpers.helpers import modify_timezone
    from hdhelpers.metadata import get_series_default_timezone

    def main(*, series):
        # entrypoint function for this component
        # ***** DO NOT EDIT LINES ABOVE *****

        # compute: each day starts at midnight of the default time zone of the data,
        # e.g. at midnight in "Europe/Berlin", and has 23 or 25 hours when switching
        # from or to daylight saving time
        timezone = get_series_default_timezone(series) or "UTC"
        daily_sums = modify_timezone(series, to_timezone=timezone).resample("1D").sum()

        # view: show the timestamps in the time zone of the plot target settings
        daily_sums = modify_timezone(daily_sums)

        ...

Note the explicit fallback ``or "UTC"`` in the example: Without it, ``modify_timezone`` would
use the time zone of the plot target settings if the metadata provide no default time zone,
so the results of the computation would depend on who looks at them.

For a MULTITSFRAME, each metric may have its own default time zone:

.. code-block:: python

    from hdhelpers.metadata import get_default_timezones

    def main(*, multitsframe):
        # entrypoint function for this component
        # ***** DO NOT EDIT LINES ABOVE *****

        timezones = get_default_timezones(multitsframe)
        daily_sums = {
            metric: group.set_index("timestamp")["value"]
            .tz_convert(timezones[metric] or "UTC")
            .resample("1D")
            .sum()
            for metric, group in multitsframe.groupby("metric")
        }

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

        start, end = get_queried_interval(series)
        fig.update_xaxes(range=(start, end))

        full_title = get_series_name(series) or "Level"
        fig.update_layout(yaxis_title=full_title)

        set_dt_ticks(fig)
        set_agnostic_theme(fig)

        return {"plot": fig}

