"""Shared helpers for the test suite."""

from importlib import resources


def bundled_profile_path() -> str:
    """Absolute path to the bundled FOGRA39 ICC profile.

    Resolving through importlib.resources keeps tests independent of the
    working directory pytest runs from.
    """
    return str(
        resources.files("color_analysis_tool")
        .joinpath("profiles")
        .joinpath("ISOcoated_v2_eci.icc")
    )
