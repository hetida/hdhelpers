Installation
============

hdhelpers requires Python 3.12 or newer and is included in the hetida designer runtime.
To use it in your own Python project, run the following commands in your project's
Python environment.

Core package
------------

Install the metadata and time zone helpers:

.. code-block:: console

    python -m pip install hdhelpers

For a project managed with uv, use ``uv add hdhelpers`` instead.
The core package works without Plotly.

Plotting helpers
----------------

Install the optional ``plotting`` extra to use ``hdhelpers.plotting`` and the
plotting functions exported by ``hdhelpers``:

.. code-block:: console

    python -m pip install "hdhelpers[plotting]"

With uv, use ``uv add "hdhelpers[plotting]"``. This also enables
``from hdhelpers import *``, which includes plotting exports.

Verify the installation
-----------------------

.. code-block:: console

    python -c "import hdhelpers; print(hdhelpers.__version__)"

Continue with :doc:`first_steps` for component examples or :doc:`metadata_examples`
for sample pandas data to use in a Python session.
