"""Handling of the non-required (optional) configuration values.

The required config keys (WIDTH, HEIGHT, ENTRY, EXIT, OUTPUT_FILE, PERFECT)
are handled by :mod:`config`. This module is responsible only for the
**optional keys**, applying defaults and validating them:

============  ====================================  ==============
Key           Meaning                               Default
============  ====================================  ==============
``SEED``      Random seed (reproducibility)         none (random each run)
``ALGORITHM`` Generation algorithm name             ``backtracker``
``DISPLAY``   Display mode name                     ``ascii``
``SIGN``      String to embed                       ``42``
============  ====================================  ==============

If an optional key is invalid, :class:`~errors.ConfigValueError` is raised.
This is the same exception type as required-key validation, so the caller can
handle them uniformly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Set

from display import display_names
from errors import ConfigValueError
from generator import algorithm_names
from initializer import GLYPHS

# The optional keys interpreted by this module.
OPTIONAL_KEYS: Set[str] = {"SEED", "ALGORITHM", "DISPLAY", "SIGN"}

DEFAULT_ALGORITHM = "backtracker"
DEFAULT_DISPLAY = "ascii"
DEFAULT_SIGN = "42"


@dataclass
class Options:
    """Validated optional configuration values."""

    seed: Optional[int]
    algorithm: str
    display: str
    sign: str


def _parse_seed(value: Optional[str]) -> Optional[int]:
    """Interpret ``SEED`` as an integer (``None`` if unset)."""
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        raise ConfigValueError(f"SEED must be an integer: '{value}'")


def _parse_choice(value: Optional[str], default: str,
                  allowed: list[str], key: str) -> str:
    """Validate a choice key (ALGORITHM / DISPLAY)."""
    if value is None:
        return default
    if value not in allowed:
        raise ConfigValueError(
            f"unknown {key} '{value}'. choices: {allowed}"
        )
    return value


def _parse_sign(value: Optional[str]) -> str:
    """Validate that every character of ``SIGN`` is drawable (in GLYPHS)."""
    if value is None:
        return DEFAULT_SIGN
    unknown = sorted({ch for ch in value if ch not in GLYPHS})
    if unknown:
        raise ConfigValueError(
            f"SIGN contains characters that cannot be drawn: {unknown} "
            f"(available: {sorted(GLYPHS)})"
        )
    return value


def parse_options(raw: Dict[str, str]) -> Options:
    """Extract and validate the optional values from the raw ``KEY=VALUE`` dict.

    Args:
        raw: The upper-case-key dict read from the config file. Keys other than
            optional ones are ignored (required keys are handled by
            :mod:`config`).

    Returns:
        The validated :class:`Options`.

    Raises:
        ConfigValueError: If any optional key has an invalid value.
    """
    return Options(
        seed=_parse_seed(raw.get("SEED")),
        algorithm=_parse_choice(
            raw.get("ALGORITHM"), DEFAULT_ALGORITHM, algorithm_names(),
            "ALGORITHM"),
        display=_parse_choice(
            raw.get("DISPLAY"), DEFAULT_DISPLAY, display_names(), "DISPLAY"),
        sign=_parse_sign(raw.get("SIGN")),
    )
