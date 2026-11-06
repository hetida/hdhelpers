Metadata model reference
========================

.. currentmodule:: hdhelpers.metadata.conventions

Read models with :func:`hdhelpers.metadata.read_metadata`. The returned type depends
on the metadata's data type; see :ref:`metadata-type-selection`.
All three root models are immutable, allow additional fields and provide the same
reading and update methods.

.. list-table:: Root models
   :header-rows: 1
   :widths: 30 35 35

   * - Model
     - Data
     - Value dimensions
   * - :class:`SeriesMetadata`
     - One metric in a pandas Series
     - One, named ``value``
   * - :class:`SingleTSFrameMetadata`
     - One metric in a pandas DataFrame
     - One or more value columns
   * - :class:`MultiTSFrameMetadata`
     - Metrics identified by a DataFrame's ``metric`` column
     - Value columns for each metric

The root fields are ``dataset_metadata`` (settings for the dataset), ``metrics``
(metric descriptions) and optional ``value_dimensions_shared`` (column defaults).
See :ref:`metadata-lookup-basics` for storage, missing values and shared field rules.

Reading and updating
--------------------

Using :ref:`metadata-example-data`, read a model and attach changed metadata to a
converted result. Updates return a new model; the original remains unchanged.

.. doctest:: metadata.models

   >>> meta = md.read_metadata(series, required=True)
   >>> meta.unit()
   'm'
   >>> result = series * 100
   >>> changed = meta.with_value_dimension(None, "value", unit="cm")
   >>> md.set_metadata(result, changed)
   >>> md.get_series_unit(result), meta.unit()
   ('cm', 'm')
   >>> multi = md.read_metadata(multitsframe, required=True)
   >>> multi.unit("plant_a.pressure")
   'bar'
   >>> multi.narrowed_to("plant_a.pressure").unit()
   'bar'

``metric_id`` is the value of the field selected by ``dataset_metadata.metric_key``.
It can be omitted for SeriesMetadata and SingleTSFrameMetadata; MultiTSFrameMetadata
requires it for methods reading one metric, even if only one metric is present.
``column`` selects a value dimension and defaults to ``"value"``.

Methods in the plural return dictionaries by metric ID; value-dimension methods
return nested dictionaries as ``result[metric_id][column]``. Missing fields return
None; ``metric()`` raises KeyError for an unknown metric. See
:ref:`metadata-getter-timezones`, :ref:`metadata-getter-recordings` and
:ref:`metadata-getter-aggregation` for their specific defaults.

``with_metric``, ``with_value_dimension`` and ``with_dataset_metadata`` accept field
changes as keyword arguments and validate the changed metadata. Use these methods
for updates; ``model_copy(update=...)`` does not validate replacement values.
Use :func:`hdhelpers.metadata.attrs_to_json` when exporting pandas attrs, or
``model_dump(mode="json")`` to obtain the model's convention fields directly.

Root classes and methods
------------------------

The shared methods are documented once under SeriesMetadata below. They are also
available on SingleTSFrameMetadata and MultiTSFrameMetadata. Conversion methods
change only metadata; convert the pandas data separately to match it.

.. autoclass:: SeriesMetadata(**data)
   :members: metric_ids, metric, value_dimension_info, value_dimension_infos, unit, units, measurement, measurements, name, names, display_name, display_names, short_display_name, short_display_names, metric_info, metric_infos, default_timezone, default_timezones, recording, recordings, default_aggregation_method, default_aggregation_methods, queried_interval, with_metric, with_value_dimension, with_dataset_metadata, as_singletsframe
   :undoc-members:
   :member-order: bysource

.. autoclass:: SingleTSFrameMetadata(**data)
   :members: as_series, as_multitsframe
   :member-order: bysource

.. autoclass:: MultiTSFrameMetadata(**data)
   :members: narrowed_to

Reading method guide
--------------------

.. list-table:: Shared methods
   :header-rows: 1
   :widths: 40 60

   * - Methods
     - Purpose
   * - :meth:`SeriesMetadata.metric_ids`, :meth:`~SeriesMetadata.metric`
     - List metric identifiers or retrieve a metric's metadata.
   * - :meth:`SeriesMetadata.value_dimension_info`, :meth:`~SeriesMetadata.value_dimension_infos`
     - Read a field or dotted path for one value dimension, or for all metrics and columns.
       An ordered sequence of fields specifies fallbacks, e.g. ``("display_name", "name")``.
   * - :meth:`SeriesMetadata.unit`, :meth:`~SeriesMetadata.units`,
       :meth:`~SeriesMetadata.measurement`, :meth:`~SeriesMetadata.measurements`
     - Read units or measured quantities, e.g. ``"°C"`` or ``"temperature"``.
   * - :meth:`SeriesMetadata.name`, :meth:`~SeriesMetadata.names`,
       :meth:`~SeriesMetadata.display_name`, :meth:`~SeriesMetadata.display_names`,
       :meth:`~SeriesMetadata.short_display_name`, :meth:`~SeriesMetadata.short_display_names`
     - Read names or labels with the :ref:`documented fallbacks <metadata-getter-names>`.
   * - :meth:`SeriesMetadata.metric_info`, :meth:`~SeriesMetadata.metric_infos`
     - Read a field or dotted path, searching the metric before its ``value`` dimension.
       Inherited properties are a final fallback when enabled.
   * - :meth:`SeriesMetadata.default_timezone`, :meth:`~SeriesMetadata.default_timezones`
     - Read the time zone for calculations, falling back to the dataset default.
   * - :meth:`SeriesMetadata.recording`, :meth:`~SeriesMetadata.recordings`
     - Read :class:`~hdhelpers.metadata.Recording` objects describing how values are recorded.
   * - :meth:`SeriesMetadata.default_aggregation_method`, :meth:`~SeriesMetadata.default_aggregation_methods`
     - Read explicit or inferred aggregation methods, normalizing ``AVG`` to ``MEAN``.
   * - :meth:`SeriesMetadata.queried_interval`
     - Read the requested interval as UTC datetimes.

Nested metadata
---------------

These classes describe the root models' fields. Construct them from convention
fields with ``ModelName.model_validate(mapping)``, or access them through a root
model, e.g. ``meta.metric().value_dimensions``. Required fields may accept None
where the conventions permit unknown values.

.. autoclass:: MetricMetadata(**data)

   Required fields include ``id``, ``name`` and ``value_dimensions``. Other fields
   describe labels, recording, default time zone, aggregation, comments and inherited properties.

.. autoclass:: ValueDimensionMetadata(**data)

   Required fields are ``column``, ``unit`` and ``measurement``. Unit and measurement
   may be None. Optional fields include names, data type, deadband and display precision.

.. autoclass:: SharedValueDimensionMetadata(**data)

   ``column`` identifies the value dimension. Its other fields supply shared defaults.

.. autoclass:: SingleMetricDatasetMetadata(**data)

   ``single_metric`` identifies the sole metric using ``metric_key``.

.. autoclass:: MultiTSFrameDatasetMetadata(**data)

   Both dataset models include ``metric_key``, ``queried_metrics``, the requested interval,
   default settings and adapter invalidation settings. Here ``single_metric`` is optional
   and applies only to a dataset containing one metric.

.. autoclass:: InheritedMetricMetadata(**data)

   The reading methods of the root models use these properties as fallbacks only with
   ``include_inherited=True``.

.. autoclass:: MetricComment(**data)

.. autoclass:: MetricCommentReply(**data)

.. autoclass:: SignalGroupMetadata(**data)

Allowed values and validation issues
----------------------------------------

.. autoclass:: IntervalType
   :members:

.. autoclass:: AggregationMethod
   :members:

.. autoclass:: ValueDataType
   :members:

.. autoclass:: RecordingMode
   :members:

.. autoclass:: MetadataIssueSeverity
   :members:

.. autoclass:: MetadataConventionIssue(**data)

   .. attribute:: severity
      :type: MetadataIssueSeverity

      Error for a violation; warning for a likely mistake.

   .. attribute:: location
      :type: str

      Path to the affected field, e.g. ``"metrics[0].name"``; empty for the metadata as a whole.

   .. attribute:: message
      :type: str

      Explanation of the problem.

Obtain validation issues with :func:`hdhelpers.metadata.check_metadata_conventions`.
When required metadata cannot be read, :func:`hdhelpers.metadata.read_metadata`
raises :class:`~hdhelpers.metadata.MetadataConventionError`, whose ``issues`` attribute
contains these issue objects.
