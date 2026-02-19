"""
Utility helper functions for the market_analysis project.

This module provides small reusable helpers, such as filename
sanitization for safe file saving across operating systems.
"""

import re
import unicodedata


def safe_filename(s: str) -> str:
    """
    Convert a string into a filesystem-safe filename.

    The function removes special characters, normalizes Unicode
    characters to ASCII, replaces spaces with underscores, and
    collapses repeated underscores.

    Parameters
    ----------
    s : str
        Input string.

    Returns
    -------
    str
        Sanitized filename safe for most filesystems.
    """

    s = unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("ASCII")
    s = s.strip().replace(" ", "_")
    s = re.sub(r'[<>:"/\\|?*]', "", s)
    s = re.sub(r"[^A-Za-z0-9._-]", "", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_.")
