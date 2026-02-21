"""
Unit tests for the ``market_analysis.utils`` module.

This module contains pytest-based tests for the ``safe_filename``
utility function. The tests verify correct handling of special
characters, whitespace normalization, Unicode normalization,
and various edge cases to ensure filenames are safe across
filesystems.
"""

import pytest

from market_analysis.utils import safe_filename


def test_removes_special_characters():
    assert safe_filename('file<>:"/\\|?*name') == "filename"


def test_removes_invalid_characters():
    assert safe_filename("file@#$%^&name") == "filename"


def test_replaces_spaces_with_underscores():
    assert safe_filename("my file name") == "my_file_name"


def test_collapses_multiple_underscores():
    assert safe_filename("my   file   name") == "my_file_name"


def test_trims_leading_and_trailing_spaces():
    assert safe_filename("   myfile   ") == "myfile"


def test_trims_leading_and_trailing_underscores_and_dots():
    assert safe_filename("__myfile__.") == "myfile"


def test_preserves_valid_characters():
    assert safe_filename("file_name-1.0.txt") == "file_name-1.0.txt"


def test_unicode_normalization():
    # ü → u, é → e
    assert safe_filename("für élise.txt") == "fur_elise.txt"


def test_empty_string():
    assert safe_filename("") == ""


@pytest.mark.parametrize(
    "input_string,expected",
    [
        ("BTC-USD", "BTC-USD"),
        ("S&P 500", "SP_500"),
        ("  test  file  ", "test_file"),
        ("...hidden...", "hidden"),
        ("file___name", "file_name"),
    ],
)
def test_various_cases(input_string, expected):
    assert safe_filename(input_string) == expected
