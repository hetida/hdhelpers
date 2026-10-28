.. hdhelpers documentation master file, created by
   sphinx-quickstart on Fri Mar 13 07:27:50 2026.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

#######################
hdhelpers
#######################

Introduction
============

hdhelpers is a package designed for and included in the standard installation of the `hetida designer`_.

It contains functions that streamline plotting components, especially those that are used in the `hetida platform`_, by

* accessing metadata of series, singletsframes and multitsframes that complies with the `hetida designer metadata conventions`_,
* aditional helper functions like adjusting the timezone of timestamps, series, and dataframes,
* accessing metadata that the hetida platform writes into the hetida designer's *plot_target_settings* context variable (tbd),
* providing toggleable standardized styling options and json serialization for plotly plots (tbd).

.. _hetida designer: https://github.com/hetida/hetida-designer
.. _hetida designer metadata conventions: https://hetida.github.io/hetida-designer/user_guide/attached_metadata/
.. _hetida platform: https://hetida.io/

Further Information
===================

.. toctree::
   :maxdepth: 2

   installation
   first_steps
   metadata_examples
   metadata_models

Functions
=========

metadata
-----------------

The examples below use :ref:`metadata-example-data`. See :doc:`metadata_examples`
for the return shapes and shared examples of the related getters.
See :ref:`metadata-lookup-basics` for metric selection and missing-field behavior.

.. automodule:: hdhelpers.metadata
   :members:
   :show-inheritance:


helpers
------------------

.. automodule:: hdhelpers.helpers
   :members:
   :show-inheritance:



plotting
------------------

.. automodule:: hdhelpers.plotting
   :members:
   :show-inheritance:



exceptions
-------------------

For metadata validation errors, see :class:`hdhelpers.metadata.MetadataConventionError`
in the metadata API. Its ``issues`` attribute contains the individual validation issues.

.. automodule:: hdhelpers.exceptions
   :members:
   :show-inheritance:
