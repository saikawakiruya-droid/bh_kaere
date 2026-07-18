"""Reading and validating the configuration file (``KEY=VALUE``).

This module is responsible for interpreting and validating the **required
keys**, and delegates the handling of the non-required (optional) keys to
:mod:`validation.options`.

Reading never aborts mid-file: a malformed line is a **parse error** — printed
immediately as an ``error`` (with its line number) and skipped — but the read
continues so every well-formed ``KEY=VALUE`` pair is still collected. Only then
is usability judged, and the fatal problems are reported together in one
:class:`~core.errors.ConfigError`:

- **required keys** — a missing key and an invalid value are the same class of
  fatal problem, so both are collected and raised together (validation does not
  stop at the first).
- **parse errors** — already shown immediately during the read; they also make
  the config fatal.

Everything else is only a warning and never aborts: unknown keys are ignored,
and invalid *optional* values fall back to their defaults (see
:mod:`validation.options`).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from core.errors import ConfigError, ConfigValueError
from validation.options import OPTIONAL_KEYS, Options, parse_options

Coord = Tuple[int, int]

REQUIRED_KEYS: Set[str] = {
    "WIDTH", "HEIGHT", "ENTRY", "EXIT", "OUTPUT_FILE", "PERFECT",
}


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


def _read_pairs(path: str) -> Tuple[Dict[str, str], List[str]]:
    """Read the config file into a ``KEY=VALUE`` dict (upper-case keys).

    Lines starting with ``#`` and blank lines are ignored.

    A malformed line (not in ``KEY=VALUE`` form, or with an empty key) is a
    **parse error**: it is reported immediately as an ``error`` (with its line
    number) and skipped, but the read still continues, collecting every
    well-formed pair. Reading never aborts here (except when the file itself
    cannot be opened); whether the config is usable is decided by
    :func:`parse_config`.

    Returns:
        ``(pairs, parse_errors)`` — the collected pairs and the list of parse
        error messages already printed (empty when every line was well-formed).

    Raises:
        ConfigError: If the file does not exist or cannot be read.
    """
    pairs: Dict[str, str] = {}
    parse_errors: List[str] = []
    try:
        # utf-8-sig reads the first key correctly even for BOM-prefixed files.
        with open(path, encoding="utf-8-sig") as fh:
            for lineno, line in enumerate(fh, 1):
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if "=" not in stripped:
                    msg = (f"line {lineno}: not in 'KEY=VALUE' form: "
                           f"{line.rstrip()!r}")
                    print(f"error: {msg}", file=sys.stderr)
                    parse_errors.append(msg)
                    continue
                key, value = stripped.split("=", 1)
                key = key.strip().upper()
                if not key:
                    msg = f"line {lineno}: empty key: {line.rstrip()!r}"
                    print(f"error: {msg}", file=sys.stderr)
                    parse_errors.append(msg)
                    continue
                if key in pairs:
                    # Reassignment is allowed, but warn to avoid oversights.
                    print(f"warning: line {lineno}: duplicate key {key} "
                          f"(using the later value)", file=sys.stderr)
                pairs[key] = value.strip()
    except FileNotFoundError:
        raise ConfigError(f"config file not found: {path}")
    except OSError as err:
        raise ConfigError(f"cannot read config file: {path} ({err})")
    return pairs, parse_errors


def _parse_positive_int(raw: Dict[str, str], key: str) -> int:
    """Interpret a positive-integer key (WIDTH / HEIGHT)."""
    value = raw[key]
    try:
        num = int(value)
    except ValueError:
        raise ConfigValueError(
            f"{key} must be an integer: '{value}'"
        ) from None
    if num <= 0:
        raise ConfigValueError(f"{key} must be 1 or greater: {num}")
    return num


def _parse_coord(raw: Dict[str, str], key: str,
                 width: Optional[int], height: Optional[int]) -> Coord:
    """Interpret an ``x,y`` coordinate key (ENTRY / EXIT) and validate range.

    The range check is skipped when ``width``/``height`` are ``None`` (i.e. they
    failed to parse).
    """
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
        ) from None
    if width is not None and height is not None:
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
    ) from None


def parse_config(path: str) -> Config:
    """Read the config file and return a validated :class:`Config`.

    Args:
        path: Path to the config file.

    Returns:
        The validated configuration.

    Raises:
        ConfigError: If the config cannot be used. For the required keys, a
            missing key and an invalid value are the same class of fatal
            problem, so both are collected and reported together in one message
            (validation does not stop at the first). Parse errors from the read
            (malformed lines) are shown immediately and also make this fatal.
            Non-fatal issues — invalid *optional* values and unknown keys — are
            only warnings and never reach here.
    """
    raw, parse_errors = _read_pairs(path)

    # Unknown keys are most likely typos. The spec allows extra keys, so this
    # is not fatal: warn and continue.
    unknown = raw.keys() - REQUIRED_KEYS - OPTIONAL_KEYS
    if unknown:
        print(f"warning: ignoring unknown config key(s): {sorted(unknown)}",
              file=sys.stderr)

    # Optional keys never abort (invalid values warn + fall back to a default),
    # so parse them up-front: their warnings are always shown, even when a
    # required key below turns out to be fatal.
    options = parse_options(raw)

    # Collect every required-key problem — missing keys and invalid values
    # alike — instead of failing on the first, so the user sees all of them at
    # once. Each field is parsed independently; on failure its slot stays None
    # and downstream checks that depend on it are skipped so one failure never
    # masks another.
    errors: List[str] = [
        f"missing required key: {key}"
        for key in sorted(REQUIRED_KEYS - raw.keys())
    ]

    def _try(key, parse):  # type: ignore[no-untyped-def]
        if key not in raw:  # already recorded as missing above
            return None
        try:
            return parse()
        except ConfigValueError as err:
            errors.append(str(err))
            return None

    width = _try("WIDTH", lambda: _parse_positive_int(raw, "WIDTH"))
    height = _try("HEIGHT", lambda: _parse_positive_int(raw, "HEIGHT"))
    entry = _try("ENTRY", lambda: _parse_coord(raw, "ENTRY", width, height))
    exit_ = _try("EXIT", lambda: _parse_coord(raw, "EXIT", width, height))
    if entry is not None and exit_ is not None and entry == exit_:
        errors.append(f"ENTRY and EXIT must differ: {entry}")

    output_file = raw.get("OUTPUT_FILE", "").strip()
    if "OUTPUT_FILE" in raw and not output_file:
        errors.append("OUTPUT_FILE is empty")

    perfect = _try("PERFECT", lambda: _parse_bool(raw, "PERFECT"))

    # Parse errors were already printed immediately during the read; a bullet
    # here ties them into the final "why we are aborting" summary.
    if parse_errors:
        errors.append(f"{len(parse_errors)} malformed line(s) could not be "
                      f"parsed (see error(s) above)")

    if errors:
        raise ConfigError(
            "the config has the following problem(s):\n  - "
            + "\n  - ".join(errors)
        )

    # Reaching here means every required value parsed; assert for the type
    # checker (each is guaranteed non-None once `errors` is empty).
    assert (width is not None and height is not None and entry is not None
            and exit_ is not None and perfect is not None)

    # A playable (PERFECT=False) board needs the four corners and centre to be
    # open corridors and at least two independent loops. Both are geometrically
    # impossible unless (WIDTH-1)*(HEIGHT-1) >= 2 -- i.e. a 1-wide frame (WIDTH
    # or HEIGHT == 1) or a 2x2 frame can never be playable, whatever the seed.
    # Rather than generate a board that always fails post-generation checks,
    # warn and fall back to a PERFECT maze, which any frame can satisfy.
    if not perfect and (width - 1) * (height - 1) < 2:
        print(
            f"warning: {width}x{height} is too small for a playable board "
            f"((WIDTH-1)*(HEIGHT-1) < 2); generating a PERFECT maze instead",
            file=sys.stderr,
        )
        perfect = True

    return Config(
        width=width,
        height=height,
        entry=entry,
        exit=exit_,
        output_file=output_file,
        perfect=perfect,
        options=options,
    )
