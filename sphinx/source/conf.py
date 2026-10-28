# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "hdhelpers"
copyright = "2026, Steffen Wittkamp, Jenny Kupzig"
author = "Steffen Wittkamp, Jenny Kupzig"
release = "-"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = []

templates_path = ["_templates"]
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "classic"  #'sphinxdoc'
html_theme_options = {
    "sidebarwidth": 350,
    "body_min_width": 0,
    "body_max_width": 1600,
}

html_static_path = ["_static"]
html_favicon = "_static/favicon.ico"
templates_path = ["_templates"]
html_css_files = [
    "stylesheet.css",
]


extensions = [
    "sphinx.ext.autodoc",   # docstrings to documentation
    "sphinx.ext.napoleon",  # enables Sphinx to parse both NumPy and Google style docstrings
    "sphinx.ext.doctest",   # enabled embedding and testing Python code examples in documentation
    "sphinx.ext.viewcode",  # add source code links
]

autosummary_generate = False
autodoc_typehints = "signature"
viewcode_line_numbers = True # line numbers in displayed source code
toc_object_entries_show_parents = "hide"  # hide class name in Table of Contents
napoleon_use_rtype = False # avoid return types as additonal line in docs

# -- setting hdhelpers on path to be importable --

import re
import sys
from html import escape
from pathlib import Path

from docutils import nodes
from sphinx.environment.adapters.toctree import TocTree

sys.path.insert(0, str(Path("..", "src", "hdhelpers").resolve()))

doctest_global_setup = """
from hdhelpers import *
from hdhelpers.metadata import *
from hdhelpers.helpers import *
from hdhelpers.plotting import *
""" + (Path(__file__).resolve().parent / "_examples" / "metadata_setup.py").read_text(
    encoding="utf-8"
)


def add_sidebar_titles(app, pagename, _templatename, context, doctree):
    """Add native tooltips with the full text of each local sidebar link."""
    if doctree is None:
        return

    toc = TocTree(app.env).get_toc_for(pagename, app.builder)
    for reference in toc.findall(nodes.reference):
        reference["reftitle"] = reference.astext()
    context["toc"] = app.builder.render_partial(toc)["fragment"]


def fix_source_backlinks(app, pagename, _templatename, context, _doctree):
    """Resolve source backlinks when a module is documented through several import paths."""
    if not pagename.startswith("_modules/"):
        return

    module = pagename.removeprefix("_modules/").replace("/", ".")
    objects = app.env.get_domain("py").objects

    def replace_link(match):
        entry = objects.get(f"{module}.{match[2]}")
        if entry is None:
            return match[0]
        target = app.builder.get_relative_uri(pagename, entry.docname) + "#" + entry.node_id
        return match[1] + escape(target, quote=True) + match[3]

    # Sphinx viewcode otherwise uses the first documented import path for every backlink.
    context["body"] = re.sub(
        r'(<div class="viewcode-block" id="([^"]+)">\s*'
        r'<a class="viewcode-back" href=")[^"]+(">)',
        replace_link,
        context.get("body", ""),
    )


def setup(app):
    app.connect("html-page-context", add_sidebar_titles)
    app.connect("html-page-context", fix_source_backlinks)
