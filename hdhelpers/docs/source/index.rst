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

* accessing series metadata that complies with the hetida platform metadata scheme
* accessing metadata that the hetida platform writes into the hetida designer's *plot_target_settings* context variable
* adjusting the timezone of timestamps, series, and dataframes
* providing toggleable standardized styling options and json serialization for plotly plots

.. _hetida designer: https://github.com/hetida/hetida-designer
.. _hetida platform: https://hetida.io/

Further Information
===================

.. toctree::
   :maxdepth: 2

   first_steps

Functions
=========

.. automodule:: hdhelpers
   :members:
   :show-inheritance:
