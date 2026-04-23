project = 'market-analysis'
copyright = '2026, Marco Zank'
author = 'Marco Zank'
release = '0.1.0'

extensions = [
    'autodoc2',
    'myst_parser',
    'sphinx_rtd_theme',
]

exclude_patterns = ['_build']

html_theme = 'sphinx_rtd_theme'

autodoc2_packages = [
    "../src/market_analysis",
]
autodoc2_render_plugin = "myst"
autodoc2_output_dir = "apidocs"
