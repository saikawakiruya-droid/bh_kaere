"""Handling of the non-required (optional) configuration values.

The required config keys (WIDTH, HEIGHT, ENTRY, EXIT, OUTPUT_FILE, PERFECT)
are handled by :mod:`validation.config`. This module is responsible only for
the **optional keys**, applying defaults and validating them:

============  ====================================  ==============
Key           Meaning                               Default
============  ====================================  ==============
``SEED``      Random seed (reproducibility)         none (random each run)
``ALGORITHM`` Generation algorithm name             ``backtracker``
``DISPLAY``   Display mode name                     ``ascii``
``SIGN``      Only 2 and 4 are drawable             ``42``
============  ====================================  ==============

Optional keys are **non-fatal**: if a value is invalid, a warning is printed
and the default is used instead, so generation continues. (Contrast with the
required keys in :mod:`validation.config`, where a missing key aborts.)
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from generation.generator import algorithm_names
from generation.initializer import GLYPHS
from output.display import display_names

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
    """Interpret ``SEED`` as an integer (``None`` if unset or invalid)."""
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        print(f"warning: SEED must be an integer: '{value}' "
              f"(ignoring, using a random seed)", file=sys.stderr)
        return None


def _parse_choice(value: Optional[str], default: str,
                  allowed: List[str], key: str) -> str:
    """Validate a choice key (ALGORITHM / DISPLAY); fall back to default."""
    if value is None:
        return default
    if value not in allowed:
        print(f"warning: unknown {key} '{value}'. choices: {allowed} "
              f"(using default '{default}')", file=sys.stderr)
        return default
    return value


def _parse_sign(value: Optional[str]) -> str:
    """Validate that every character of ``SIGN`` is drawable (in GLYPHS)."""
    if value is None:
        return DEFAULT_SIGN
    unknown = sorted({ch for ch in value if ch not in GLYPHS})
    if unknown:
        print(f"warning: SIGN contains characters that cannot be drawn: "
              f"{unknown} (available: {sorted(GLYPHS)}; "
              f"using default '{DEFAULT_SIGN}')", file=sys.stderr)
        return DEFAULT_SIGN
    return value


def parse_options(raw: Dict[str, str]) -> Options:
    """Extract and validate the optional values from the raw ``KEY=VALUE`` dict.

    Args:
        raw: The upper-case-key dict read from the config file. Keys other than
            optional ones are ignored (required keys are handled by
            :mod:`validation.config`).

    Returns:
        The validated :class:`Options`. Invalid optional values are replaced
        with their defaults (after a warning), so this never raises.
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
