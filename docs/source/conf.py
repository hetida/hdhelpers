# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'hdhelpers'
copyright = '2026, Steffen Wittkamp, Jenny Kupzig, Christoph Dingel'
author = 'Steffen Wittkamp, Jenny Kupzig, Christoph Dingel'
release = '-'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = []

templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme =  'nature' #'sphinxdoc'
html_static_path = ['_static']
templates_path = ["_templates"]

extensions = [
    'sphinx.ext.autodoc', # docstrings to documentation
    'sphinx.ext.napoleon', # enables Sphinx to parse both NumPy and Google style docstrings
    'sphinx.ext.doctest' # enabled embedding and testing Python code examples in documentation
]

autosummary_generate = False
autodoc_typehints = "description"
toc_object_entries_show_parents= 'hide' # hide class name in Table of Contents

# -- setting hdhelpers on path to be importable --

import sys
from pathlib import Path

sys.path.insert(0, str(Path('..', 'src','hdhelpers').resolve()))

doctest_global_setup = '''
try:
    import pandas as pd
except ImportError:
    pd = None
'''
