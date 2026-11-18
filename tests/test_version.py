"""
Tests for the single-source version handling.

The canonical version lives in pyproject.toml and is exposed as installed
distribution metadata. The package, the Sphinx configuration and CITATION.cff
must all agree with it.
"""

import re
import runpy
from importlib.metadata import version
from pathlib import Path

import market_analysis

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_package_version_matches_distribution_metadata() -> None:
    assert market_analysis.__version__ == version("market-analysis")


def test_docs_release_matches_package_version() -> None:
    conf = runpy.run_path(str(REPO_ROOT / "docs" / "conf.py"))
    assert conf["release"] == market_analysis.__version__


def test_docs_config_does_not_shadow_sphinx_version() -> None:
    conf = runpy.run_path(str(REPO_ROOT / "docs" / "conf.py"))
    assert not callable(conf.get("version"))


def test_citation_version_matches_package_version() -> None:
    citation = (REPO_ROOT / "CITATION.cff").read_text(encoding="utf-8")
    match = re.search(r"^version:\s*(\S+)\s*$", citation, flags=re.MULTILINE)
    assert match is not None
    assert match.group(1) == market_analysis.__version__
