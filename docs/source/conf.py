from typing import Any

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project: str = ""
copyright: str = "2023, "
author: str = ""
release: str = "unstable alpha 0.1"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions: list[str] = [
    "sphinx-autoapi",
    "numpydoc",
    "sphinx-autodoc-typehints",
    "autosummary",
]

templates_path: list[str] = ["_templates"]
exclude_patterns: list[Any] = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme: str = "sphinx-book-theme"
html_static_path: list[str] = ["_static"]
