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

* accessing series metadata that complies with the hetida platform metadata scheme,
* aditional helper functions like adjusting the timezone of timestamps, series, and dataframes,
* accessing metadata that the hetida platform writes into the hetida designer's *plot_target_settings* context variable (tbd),
* providing toggleable standardized styling options and json serialization for plotly plots (tbd).

.. _hetida designer: https://github.com/hetida/hetida-designer
.. _hetida platform: https://hetida.io/

Further Information
===================

.. toctree::
   :maxdepth: 2

   first_steps

Functions
=========

metadata
-----------------

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

.. automodule:: hdhelpers.exceptions
   :members:
   :show-inheritance:
