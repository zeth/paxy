# docs/conf.py
# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html


import sys
from pathlib import Path
from sphinx.highlighting import lexers

EXT_DIR = (Path(__file__).parent / "_ext").resolve()
sys.path.insert(0, str(EXT_DIR))  # now 'import paxy_lexer' works

from paxy_lexer import PaxyLexer


# Make the project importable and add our _ext/ to sys.path
DOCS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = DOCS_DIR.parents[1]
EXT_DIR = DOCS_DIR / "_ext"

sys.path.insert(0, str(PROJECT_ROOT))  # import paxy
sys.path.insert(0, str(EXT_DIR))  # import commands_autogen


# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "Paxy"
author = "Paxy contributors (Zeth so far)"
copyright = "2025, Paxy contributors (Zeth so far)"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "alabaster"
html_static_path = ["_static"]


project = "Paxy"

# Optional: get version from package
try:
    import paxy as _paxy  # type: ignore

    release = getattr(_paxy, "__version__", "0.0.0")
except Exception:
    release = "0.1"

extensions = [
    "myst_parser",
    "commands_autogen",  # our generator extension
]

myst_enable_extensions = ["colon_fence"]


# Register for both names so you don't have to edit existing fences
lexers["paxy"] = PaxyLexer()
lexers["basic"] = PaxyLexer()  # alias for existing ```basic blocks

# (Optional) make Paxy the default for untagged code blocks in this doc set
highlight_language = "paxy"
