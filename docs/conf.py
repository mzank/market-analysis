from importlib.metadata import PackageNotFoundError, version

project = "market-analysis"
copyright = "2026, Marco Zank"
author = "Marco Zank"

try:
    # Keep the documentation version in sync with pyproject.toml.
    release = version("market-analysis")
except PackageNotFoundError:  # building docs from an uninstalled source checkout
    release = "0.0.0"

extensions = [
    "autodoc2",
    "myst_parser",
    "sphinx_rtd_theme",
]

exclude_patterns = ["_build"]

html_theme = "sphinx_rtd_theme"

autodoc2_packages = [
    "../src/market_analysis",
]
autodoc2_render_plugin = "myst"
autodoc2_output_dir = "apidocs"

autodoc_typehints = "description"
autodoc_typehints_format = "short"

nitpick_ignore = [
    ("py:class", "pandas.DataFrame"),
    ("py:class", "pandas.Series"),
    ("py:class", "pandas._typing.TimestampConvertibleTypes"),
]
