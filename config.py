"""Reading and validating the configuration file (``KEY=VALUE``).

CLI-specific glue: this module owns the assignment's config-file format (not
part of the reusable :mod:`engine` package). It is split into two sections:

1. **Required keys** (``WIDTH``, ``HEIGHT``, ``ENTRY``, ``EXIT``,
   ``OUTPUT_FILE``, ``PERFECT``) — the maze cannot be built without them.
2. **Optional keys** (``SEED``, ``ALGORITHM``, ``DISPLAY``, ``SIGN``) — each has
   a default, applied and validated by :func:`parse_options`.

When validation fails, it raises a distinct exception depending on the cause:

- :class:`~engine.errors.ConfigParseError` — syntax error (a non-``KEY=VALUE``
  line)
- :class:`~engine.errors.ConfigKeyError`   — a required key is missing
- :class:`~engine.errors.ConfigValueError` — an invalid value (type / range /
  coord), for either a required or an optional key

All of them derive from :class:`~engine.errors.ConfigError`, so the caller can
catch them together as "a fatal error that prevents building the maze".
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Dict, Optional, Set, Tuple

from engine.build import GLYPHS, algorithm_names
from engine.errors import (
    ConfigError,
    ConfigKeyError,
    ConfigParseError,
    ConfigValueError,
)
from engine.output import display_names

Coord = Tuple[int, int]

REQUIRED_KEYS: Set[str] = {
    "WIDTH", "HEIGHT", "ENTRY", "EXIT", "OUTPUT_FILE", "PERFECT",
}

# ===========================================================================
# Optional keys (SEED / ALGORITHM / DISPLAY / SIGN), each with a default
# ===========================================================================

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
            optional ones are ignored (required keys are handled below).

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


# ===========================================================================
# Required keys (WIDTH / HEIGHT / ENTRY / EXIT / OUTPUT_FILE / PERFECT)
# ===========================================================================


@dataclass
class Config:
    """The whole validated configuration (required keys + :class:`Options`)."""

    width: int
    height: int
    entry: Coord
    exit: Coord
    output_file: str
    perfect: bool
    options: Options


def _read_pairs(path: str) -> Dict[str, str]:
    """Read the config file and return a ``KEY=VALUE`` dict (upper-case keys).

    Lines starting with ``#`` and blank lines are ignored.

    Raises:
        ConfigError: If the file does not exist or cannot be read.
        ConfigParseError: If a line is not in ``KEY=VALUE`` form.
    """
    pairs: Dict[str, str] = {}
    try:
        # utf-8-sig reads the first key correctly even for BOM-prefixed files.
        with open(path, encoding="utf-8-sig") as fh:
            for lineno, line in enumerate(fh, 1):
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if "=" not in stripped:
                    raise ConfigParseError(
                        f"line {lineno}: not in 'KEY=VALUE' form: "
                        f"{line.rstrip()!r}"
                    )
                key, value = stripped.split("=", 1)
                key = key.strip().upper()
                if not key:
                    raise ConfigParseError(f"line {lineno}: empty key")
                if key in pairs:
                    # Reassignment is allowed, but warn to avoid oversights.
                    print(f"warning: line {lineno}: duplicate key {key} "
                          f"(using the later value)", file=sys.stderr)
                pairs[key] = value.strip()
    except FileNotFoundError:
        raise ConfigError(f"config file not found: {path}")
    except OSError as err:
        raise ConfigError(f"cannot read config file: {path} ({err})")
    return pairs


def _parse_positive_int(raw: Dict[str, str], key: str) -> int:
    """Interpret a positive-integer key (WIDTH / HEIGHT)."""
    value = raw[key]
    try:
        num = int(value)
    except ValueError:
        raise ConfigValueError(f"{key} must be an integer: '{value}'")
    if num <= 0:
        raise ConfigValueError(f"{key} must be 1 or greater: {num}")
    return num


def _parse_coord(raw: Dict[str, str], key: str,
                 width: int, height: int) -> Coord:
    """Interpret an ``x,y`` coordinate key (ENTRY / EXIT) and validate range."""
    value = raw[key]
    parts = value.split(",")
    if len(parts) != 2:
        raise ConfigValueError(
            f"{key} must be in 'x,y' form: '{value}'"
        )
    try:
        x, y = int(parts[0]), int(parts[1])
    except ValueError:
        raise ConfigValueError(
            f"{key} coordinates must be integers: '{value}'"
        )
    if not (0 <= x < width and 0 <= y < height):
        raise ConfigValueError(
            f"{key} ({x},{y}) is outside the maze bounds {width}x{height}"
        )
    return (x, y)


def _parse_bool(raw: Dict[str, str], key: str) -> bool:
    """Interpret a boolean key (PERFECT)."""
    value = raw[key].strip().lower()
    if value in ("true", "1", "yes"):
        return True
    if value in ("false", "0", "no"):
        return False
    raise ConfigValueError(
        f"{key} must be True / False: '{raw[key]}'"
    )


def parse_config(path: str) -> Config:
    """Read the config file and return a validated :class:`Config`.

    Args:
        path: Path to the config file.

    Returns:
        The validated configuration.

    Raises:
        ConfigError: If the configuration is invalid and the maze cannot be
            built (the cause is distinguished by subclass).
    """
    raw = _read_pairs(path)

    missing = REQUIRED_KEYS - raw.keys()
    if missing:
        raise ConfigKeyError(
            f"missing required keys: {sorted(missing)}"
        )

    # Unknown keys are most likely typos. The spec allows extra keys, so this
    # is not fatal: warn and continue.
    unknown = raw.keys() - REQUIRED_KEYS - OPTIONAL_KEYS
    if unknown:
        print(f"warning: ignoring unknown config key(s): {sorted(unknown)}",
              file=sys.stderr)

    width = _parse_positive_int(raw, "WIDTH")
    height = _parse_positive_int(raw, "HEIGHT")
    entry = _parse_coord(raw, "ENTRY", width, height)
    exit_ = _parse_coord(raw, "EXIT", width, height)
    if entry == exit_:
        raise ConfigValueError(
            f"ENTRY and EXIT must differ: {entry}"
        )

    output_file = raw["OUTPUT_FILE"].strip()
    if not output_file:
        raise ConfigValueError("OUTPUT_FILE is empty")

    perfect = _parse_bool(raw, "PERFECT")
    options = parse_options(raw)

    return Config(
        width=width,
        height=height,
        entry=entry,
        exit=exit_,
        output_file=output_file,
        perfect=perfect,
        options=options,
    )
