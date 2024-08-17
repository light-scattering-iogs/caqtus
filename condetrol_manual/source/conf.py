# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
import shutil

from polars.dependencies import subprocess

from condetrol_manual.source.generate_figures import generate_figures

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "Condetrol"
copyright = "2024, caqtus"
author = "caqtus"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ["sphinx.ext.autosectionlabel"]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "alabaster"
html_static_path = ["_static"]

rst_prolog = """
.. |project| replace:: Condetrol
.. |shot| replace:: :ref:`shot <Shot>`
.. |sequence| replace:: :ref:`sequence <Sequence>`
.. |expression| replace:: :ref:`expression <Expression>`
"""

generate_figures()


def finished(app, exception):
    if app.builder.name == "qthelp":
        result = subprocess.run(["qhelpgenerator", "build/qthelp/Condetrol.qhcp"])
        result.check_returncode()
        shutil.move(
            "build/qthelp/Condetrol.qch", "../caqtus/gui/condetrol/_help/Condetrol.qch"
        )
        shutil.move(
            "build/qthelp/Condetrol.qhc", "../caqtus/gui/condetrol/_help/Condetrol.qhc"
        )


def setup(app):
    app.connect("build-finished", finished)
