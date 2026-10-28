Metadata examples
=================

.. _metadata-example-data:

Shared data setup
-----------------

The following examples use pandas objects with metadata. In hetida designer, these
are supplied as component inputs. To try the examples in a Python session, create
them using the shared data setup below.

The setup creates three independent pandas objects with complete metadata following
the current conventions. Use these objects for the API reference examples as well:

* ``series``: a SERIES with one value per timestamp, measured in metres.
* ``dataframe``: a SINGLETSFRAME describing one metric with the value columns
  ``value`` (temperature) and ``state`` (measurement state).
* ``multitsframe``: a MULTITSFRAME with pressure and temperature metrics, whose
  identifiers are stored in the ``metric`` column.

``md`` is the imported ``hdhelpers.metadata`` module. ``deepcopy`` keeps changes to
the example metadata independent of the supplied templates. The same setup is run
for each documentation test group. To start an example again with unchanged data,
rerun the setup.

.. literalinclude:: _examples/metadata_setup.py
   :language: python

See :doc:`first_steps` for examples within components.

.. _metadata-lookup-basics:

Metadata lookup basics
----------------------

A metric is one measured signal. A value column (called a *value dimension* in the
schema) holds values or related information, such as measurement state. Metadata
is stored in ``attrs`` as convention fields or as a model under ``hd_metadata``.
Shared metadata in ``value_dimensions_shared`` supplies defaults for matching
columns across metrics.

The metadata models are immutable and allow additional fields at every level.
Metadata timestamps are UTC ISO strings with an explicit ``Z`` or ``+00:00`` offset.
Adapters exchange convention fields; :func:`hdhelpers.metadata.attrs_to_json` converts
an attached model back to those fields for export.

Series and SINGLETSFRAME getters select ``dataset_metadata.single_metric``, or the
only metric described if no identifier is set. They do not select by ``Series.name``.
Without a unique selection, metric-specific information is unavailable.
Absent fields and fields set to None count as missing. Inherited properties are supplied
by the source system for the metric or its parent assets. They are used as fallbacks when
``include_inherited=True``. Explicit paths such as ``"inherited.site"`` access them directly,
even when this fallback is disabled.
Missing or invalid metadata gives empty mappings for mapping getters; missing-key
lookups still use their documented defaults.

.. _metadata-type-selection:

Automatic metadata type selection
---------------------------------

When parsing raw attrs, ``read_metadata``, ``attach_metadata`` and
``check_metadata_conventions`` infer the type as follows:

* A Series selects ``SERIES``.
* A DataFrame with a ``metric`` column selects ``MULTITSFRAME``.
* Other DataFrames select ``SINGLETSFRAME``.

An explicit ``data_type`` overrides this selection. ``read_metadata`` also checks
the type of an attached model when requested; ``attach_metadata`` keeps an already
attached model unchanged.

.. _metadata-getter-values:

Units, measurements and return shapes
-------------------------------------

SERIES getters return a single value. SINGLETSFRAME getters return information by
value column; MULTITSFRAME getters return it by metric and value column. The
measurement describes the physical quantity, whereas the unit describes its scale.

.. doctest:: metadata.examples.values

   >>> md.get_series_unit(series), md.get_series_measurement(series)
   ('m', 'level')
   >>> dict(md.get_singlets_units(dataframe))
   {'value': '°C', 'state': None}
   >>> md.get_singlets_measurements(dataframe)["value"]
   'temperature'
   >>> md.get_units(multitsframe)["plant_a.pressure"]["value"]
   'bar'
   >>> md.get_measurements(multitsframe)["plant_a.pressure"]["value"]
   'pressure'
   >>> md.get_units(multitsframe)["unknown metric"]["value"] is None
   True
   >>> start, end = md.get_queried_interval(series)
   >>> start.isoformat(), end.isoformat()
   ('2026-01-01T00:00:00+00:00', '2026-01-02T00:00:00+00:00')

.. _metadata-getter-names:

Names and display-name fallbacks
--------------------------------

These getters use the same return shapes. A short display name falls back to the
display name, which falls back to the name. The templates omit display names, so
the examples show that fallback. See :doc:`first_steps` for the lookup order and
the optional ``include_inherited=True`` fallback to inherited properties.

.. doctest:: metadata.examples.names

   >>> md.get_series_name(series)
   'Water level north'
   >>> md.get_series_display_name(series), md.get_series_short_display_name(series)
   ('Water level north', 'Water level north')
   >>> md.get_singlets_names(dataframe)["state"]
   'measurement state'
   >>> md.get_singlets_display_names(dataframe)["state"]
   'measurement state'
   >>> md.get_singlets_short_display_names(dataframe)["state"]
   'measurement state'
   >>> md.get_names(multitsframe)["plant_a.pressure"]["value"]
   'Plant A pressure'
   >>> md.get_display_names(multitsframe)["plant_a.pressure"]["value"]
   'Plant A pressure'
   >>> md.get_short_display_names(multitsframe)["plant_a.pressure"]["value"]
   'Plant A pressure'

.. _metadata-getter-fields:

Metric fields and value-dimension fields
----------------------------------------

``get_singlets_info`` returns information for each value column, whereas
``get_singlets_metric_info`` returns one value for the metric. The Series variant
looks up its single value dimension; ``get_metric_info`` returns values by metric.
The field argument may also be a dotted path into nested metadata.

.. doctest:: metadata.examples.fields

   >>> md.get_series_info(series, "decimals")
   2
   >>> md.get_singlets_info(dataframe, "name")["state"]
   'measurement state'
   >>> md.get_singlets_metric_info(dataframe, "name")
   'ABC temperature'
   >>> md.get_metric_info(multitsframe, "name")["plant_a.pressure"]
   'Plant A pressure'

.. _metadata-getter-recordings:

Recording information
---------------------

Single-metric getters return a ``Recording`` object; ``get_recordings`` returns
these objects by metric. Access its fields to distinguish samples, periodic
recording and recording on change. Frequency, offset and time zone fall back to
the dataset metadata together, as described by :func:`hdhelpers.metadata.get_recordings`.

.. doctest:: metadata.examples.recordings

   >>> recording = md.get_series_recording(series)
   >>> recording.recording_mode, recording.data_frequency
   ('periodic', '15min')
   >>> md.get_singlets_recording(dataframe).data_frequency is None
   True
   >>> md.get_recordings(multitsframe)["plant_a.temperature"].recording_mode
   'on_change'

.. _metadata-getter-timezones:

Default time zones
------------------

A metric's time zone falls back to the dataset's default, otherwise to None.
Use an explicit fallback such as ``or "UTC"`` when choosing a time zone for a
computation. See :doc:`first_steps` for a daily aggregation example and the
distinction between computation and display time zones.

.. doctest:: metadata.examples.timezones

   >>> md.get_series_default_timezone(series)
   'Europe/Berlin'
   >>> md.get_singlets_default_timezone(dataframe) is None
   True
   >>> md.get_singlets_default_timezone(dataframe) or "UTC"
   'UTC'
   >>> md.get_default_timezones(multitsframe)["plant_a.pressure"]
   'Europe/Berlin'

.. _metadata-getter-aggregation:

Default aggregation methods
---------------------------

The getters return a method name, or method names by metric. An explicit method
wins; ``AVG`` is normalized to ``MEAN``. Otherwise, ``value_data_type`` in metadata
selects ``LAST`` for boolean/string and ``MEAN`` for other types.

.. doctest:: metadata.examples.aggregation

   >>> md.get_series_default_aggregation_method(series)
   'MEAN'
   >>> md.get_singlets_default_aggregation_method(dataframe)
   'MEAN'
   >>> md.get_default_aggregation_methods(multitsframe)["plant_a.temperature"]
   'MAX'

For the metadata lifecycle, start with :func:`hdhelpers.metadata.check_metadata_conventions`,
then :func:`hdhelpers.metadata.read_metadata` or :func:`hdhelpers.metadata.attach_metadata`.
Use :func:`hdhelpers.metadata.set_metadata` to attach changed metadata to a result
and :func:`hdhelpers.metadata.attrs_to_json` before serialization. Each function
has an example using the shared data setup.

See :doc:`metadata_models` for the model classes and their reading, update and conversion methods.
