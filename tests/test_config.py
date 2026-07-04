# [TEST FILE] 提出・採点対象外（仕様 III.3）— 動作確認専用。実行: make test / pytest
"""Unit tests for the config / options modules (configuration validation)."""

from __future__ import annotations

from pathlib import Path

import pytest

from config import parse_config
from errors import (
    ConfigError,
    ConfigKeyError,
    ConfigParseError,
    ConfigValueError,
)

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
    with pytest.raises(ConfigKeyError):
        parse_config(_write(tmp_path, text))


def test_syntax_error(tmp_path: Path) -> None:
    text = "WIDTH=10\nHEIGHT 10\n"  # no '='
    with pytest.raises(ConfigParseError):
        parse_config(_write(tmp_path, text))


def test_file_not_found() -> None:
    with pytest.raises(ConfigError):
        parse_config("no_such_file_xyz.txt")


def test_non_integer_width(tmp_path: Path) -> None:
    text = VALID.replace("WIDTH=20", "WIDTH=abc")
    with pytest.raises(ConfigValueError):
        parse_config(_write(tmp_path, text))


def test_non_positive_width(tmp_path: Path) -> None:
    text = VALID.replace("WIDTH=20", "WIDTH=0")
    with pytest.raises(ConfigValueError):
        parse_config(_write(tmp_path, text))


def test_entry_out_of_bounds(tmp_path: Path) -> None:
    text = VALID.replace("ENTRY=0,0", "ENTRY=99,99")
    with pytest.raises(ConfigValueError):
        parse_config(_write(tmp_path, text))


def test_entry_equals_exit(tmp_path: Path) -> None:
    text = VALID.replace("EXIT=19,14", "EXIT=0,0")
    with pytest.raises(ConfigValueError):
        parse_config(_write(tmp_path, text))


def test_bad_coord_format(tmp_path: Path) -> None:
    text = VALID.replace("ENTRY=0,0", "ENTRY=0-0")
    with pytest.raises(ConfigValueError):
        parse_config(_write(tmp_path, text))


def test_bad_perfect_value(tmp_path: Path) -> None:
    text = VALID.replace("PERFECT=True", "PERFECT=maybe")
    with pytest.raises(ConfigValueError):
        parse_config(_write(tmp_path, text))


def test_unknown_algorithm(tmp_path: Path) -> None:
    text = VALID.replace("ALGORITHM=backtracker", "ALGORITHM=prim")
    with pytest.raises(ConfigValueError):
        parse_config(_write(tmp_path, text))


def test_unknown_display(tmp_path: Path) -> None:
    text = VALID.replace("DISPLAY=ascii", "DISPLAY=opengl")
    with pytest.raises(ConfigValueError):
        parse_config(_write(tmp_path, text))


def test_bad_seed(tmp_path: Path) -> None:
    text = VALID.replace("SEED=42", "SEED=xx")
    with pytest.raises(ConfigValueError):
        parse_config(_write(tmp_path, text))


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
