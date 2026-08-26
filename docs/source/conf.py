import os
import sys
sys.path.insert(0, os.path.abspath('../../src'))
from estim2py import __version__

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'estim2py'
copyright = '2026, Sissy Becky'
author = 'Sissy Becky'
release = __version__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",      # Pulls in API docs from docstrings
    "sphinx.ext.napoleon",     # Parses Google and NumPy style docstrings
    "sphinx.ext.autosummary",
]
autosummary_generate = True 

templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']

