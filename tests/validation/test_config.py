# [TEST FILE] 提出・採点対象外（仕様 III.3）— 動作確認専用。実行: make test / pytest
"""Unit tests for the config / options modules (configuration validation)."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.errors import (
    ConfigError,
    ConfigKeyError,
    ConfigParseError,
    ConfigValueError,
)
from validation.options import DEFAULT_ALGORITHM, DEFAULT_DISPLAY, DEFAULT_SIGN
from validation.config import parse_config

VALID = """
# Sample configuration
WIDTH=20
HEIGHT=15
ENTRY=0,0
EXIT=19,14
OUTPUT_FILE=maze.txt
PERFECT=True
SEED=42
ALGORITHM=backtracker
DISPLAY=ascii
"""


def _write(tmp_path: Path, text: str) -> str:
    path = tmp_path / "config.txt"
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_valid_config(tmp_path: Path) -> None:
    cfg = parse_config(_write(tmp_path, VALID))
    assert cfg.width == 20 and cfg.height == 15
    assert cfg.entry == (0, 0) and cfg.exit == (19, 14)
    assert cfg.output_file == "maze.txt"
    assert cfg.perfect is True
    assert cfg.options.seed == 42
    assert cfg.options.algorithm == "backtracker"
    assert cfg.options.display == "ascii"


def test_defaults_for_optional(tmp_path: Path) -> None:
    text = (
        "WIDTH=10\nHEIGHT=10\nENTRY=0,0\nEXIT=9,9\n"
        "OUTPUT_FILE=m.txt\nPERFECT=False\n"
    )
    cfg = parse_config(_write(tmp_path, text))
    assert cfg.options.seed is None
    assert cfg.options.algorithm == "backtracker"
    assert cfg.options.display == "ascii"
    assert cfg.perfect is False


def test_missing_required_key(tmp_path: Path) -> None:
    text = "WIDTH=10\nHEIGHT=10\nENTRY=0,0\nEXIT=9,9\nPERFECT=True\n"
    with pytest.raises(ConfigError) as excinfo:
        parse_config(_write(tmp_path, text))
    # OUTPUT_FILE is missing and reported by name.
    assert "OUTPUT_FILE" in str(excinfo.value)


def test_malformed_line_is_reported_immediately_as_error(
        tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # A non-'KEY=VALUE' line is a parse error: reported immediately as an
    # 'error' (not a warning), skipped, and fatal once reading completes.
    text = VALID + "this is not a valid line\n"
    with pytest.raises(ConfigError):
        parse_config(_write(tmp_path, text))
    err = capsys.readouterr().err
    assert "error:" in err and "not in 'KEY=VALUE' form" in err


def test_malformed_required_line_reported_as_error_and_missing(
        tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # A malformed line for a required key is caught twice, as intended: an
    # immediate parse error, and — since the key never entered the dict — a
    # 'missing required key' entry in the aggregated report.
    text = "WIDTH=10\nHEIGHT 10\nENTRY=0,0\nEXIT=9,9\nOUTPUT_FILE=m.txt\nPERFECT=True\n"
    with pytest.raises(ConfigError) as excinfo:
        parse_config(_write(tmp_path, text))
    err = capsys.readouterr().err
    assert "error:" in err and "not in 'KEY=VALUE' form" in err
    assert "missing required key: HEIGHT" in str(excinfo.value)


def test_file_not_found() -> None:
    with pytest.raises(ConfigError):
        parse_config("no_such_file_xyz.txt")


def test_non_integer_width(tmp_path: Path) -> None:
    text = VALID.replace("WIDTH=20", "WIDTH=abc")
    with pytest.raises(ConfigError):
        parse_config(_write(tmp_path, text))


def test_non_positive_width(tmp_path: Path) -> None:
    text = VALID.replace("WIDTH=20", "WIDTH=0")
    with pytest.raises(ConfigError):
        parse_config(_write(tmp_path, text))


def test_entry_out_of_bounds(tmp_path: Path) -> None:
    text = VALID.replace("ENTRY=0,0", "ENTRY=99,99")
    with pytest.raises(ConfigError):
        parse_config(_write(tmp_path, text))


def test_entry_equals_exit(tmp_path: Path) -> None:
    text = VALID.replace("EXIT=19,14", "EXIT=0,0")
    with pytest.raises(ConfigError):
        parse_config(_write(tmp_path, text))


def test_bad_coord_format(tmp_path: Path) -> None:
    text = VALID.replace("ENTRY=0,0", "ENTRY=0-0")
    with pytest.raises(ConfigError):
        parse_config(_write(tmp_path, text))


def test_bad_perfect_value(tmp_path: Path) -> None:
    text = VALID.replace("PERFECT=True", "PERFECT=maybe")
    with pytest.raises(ConfigError):
        parse_config(_write(tmp_path, text))


def test_unknown_algorithm_warns_and_uses_default(
        tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    text = VALID.replace("ALGORITHM=backtracker", "ALGORITHM=prim")
    cfg = parse_config(_write(tmp_path, text))
    assert cfg.options.algorithm == DEFAULT_ALGORITHM
    err = capsys.readouterr().err
    assert "ALGORITHM" in err and "prim" in err


def test_unknown_display_warns_and_uses_default(
        tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    text = VALID.replace("DISPLAY=ascii", "DISPLAY=opengl")
    cfg = parse_config(_write(tmp_path, text))
    assert cfg.options.display == DEFAULT_DISPLAY
    err = capsys.readouterr().err
    assert "DISPLAY" in err and "opengl" in err


def test_bad_seed_warns_and_uses_random(
        tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    text = VALID.replace("SEED=42", "SEED=xx")
    cfg = parse_config(_write(tmp_path, text))
    assert cfg.options.seed is None  # falls back to a random seed
    assert "SEED" in capsys.readouterr().err


def test_bad_sign_warns_and_uses_default(
        tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    text = VALID + "SIGN=abc\n"  # 'a','b','c' are not drawable glyphs
    cfg = parse_config(_write(tmp_path, text))
    assert cfg.options.sign == DEFAULT_SIGN
    assert "SIGN" in capsys.readouterr().err


def test_all_value_errors_reported_together(tmp_path: Path) -> None:
    # Several invalid required values at once are all reported in one message,
    # not just the first one encountered.
    text = (
        "WIDTH=abc\nHEIGHT=0\nENTRY=0-0\nEXIT=99,99\n"
        "OUTPUT_FILE=\nPERFECT=maybe\n"
    )
    with pytest.raises(ConfigError) as excinfo:
        parse_config(_write(tmp_path, text))
    msg = str(excinfo.value)
    assert "WIDTH" in msg
    assert "HEIGHT" in msg
    assert "ENTRY" in msg
    assert "OUTPUT_FILE" in msg
    assert "PERFECT" in msg


def test_missing_and_invalid_reported_together(tmp_path: Path) -> None:
    # A missing required key and an invalid required value are the same class of
    # fatal problem and appear together in the one aggregated message.
    text = "WIDTH=abc\nENTRY=0,0\nEXIT=9,9\nOUTPUT_FILE=m.txt\nPERFECT=True\n"
    with pytest.raises(ConfigError) as excinfo:
        parse_config(_write(tmp_path, text))
    msg = str(excinfo.value)
    assert "missing required key: HEIGHT" in msg   # missing
    assert "WIDTH must be an integer" in msg        # invalid value


def test_bom_config_is_read(tmp_path: Path) -> None:
    # WIDTH is read correctly even with a leading UTF-8 BOM.
    path = tmp_path / "config.txt"
    path.write_text(VALID, encoding="utf-8-sig")
    cfg = parse_config(str(path))
    assert cfg.width == 20


def test_unknown_key_warns_but_continues(
        tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    text = VALID + "WITDH=99\n"  # typo of WIDTH (unknown key)
    cfg = parse_config(_write(tmp_path, text))
    assert cfg.width == 20  # existing value is kept
    err = capsys.readouterr().err
    assert "unknown config key" in err and "WITDH" in err


def test_duplicate_key_warns_and_last_wins(
        tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # WIDTH defined twice -> use the later value while warning.
    text = VALID + "WIDTH=33\n"
    cfg = parse_config(_write(tmp_path, text))
    assert cfg.width == 33  # last wins
    err = capsys.readouterr().err
    assert "duplicate" in err and "WIDTH" in err


def test_errors_are_distinct() -> None:
    # Syntax / key / value errors are distinguishable as separate classes.
    assert issubclass(ConfigParseError, ConfigError)
    assert issubclass(ConfigKeyError, ConfigError)
    assert issubclass(ConfigValueError, ConfigError)
    for a, b in [(ConfigParseError, ConfigKeyError),
                 (ConfigKeyError, ConfigValueError),
                 (ConfigValueError, ConfigParseError)]:
        assert not issubclass(a, b)
