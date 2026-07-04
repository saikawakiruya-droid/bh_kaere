# [TEST FILE] 提出・採点対象外（仕様 III.3）— 動作確認専用。実行: make test / pytest
"""Integration tests for the a_maze_ing main program."""

from __future__ import annotations

from pathlib import Path

import builtins
from typing import Iterator

import pytest

from a_maze_ing import build_maze, interact, main, run
from config import parse_config
from validator import _parse_output_file, validate

CONFIG = """
WIDTH=25
HEIGHT=20
ENTRY=0,0
EXIT=24,19
OUTPUT_FILE={out}
PERFECT=True
SEED=7
"""


def _config(tmp_path: Path, out: str) -> str:
    path = tmp_path / "config.txt"
    path.write_text(CONFIG.format(out=out), encoding="utf-8")
    return str(path)


def test_end_to_end_produces_valid_output(tmp_path: Path) -> None:
    out = str(tmp_path / "maze.txt")
    code = run(_config(tmp_path, out))
    assert code == 0
    # The output file is written and satisfies the structural conditions.
    maze, entry, exit_, path = _parse_output_file(out)
    assert validate(maze, entry, exit_, solution=path) == []


def test_reproducible_with_seed(tmp_path: Path) -> None:
    out1 = str(tmp_path / "a.txt")
    out2 = str(tmp_path / "b.txt")
    run(_config(tmp_path, out1))
    # Same seed -> same output.
    cfg2 = tmp_path / "config2.txt"
    cfg2.write_text(CONFIG.format(out=out2), encoding="utf-8")
    run(str(cfg2))
    assert Path(out1).read_text() == Path(out2).read_text()


def test_missing_config_returns_error() -> None:
    assert run("does_not_exist_zzz.txt") == 1


def test_no_args_usage() -> None:
    assert main([]) == 2


def _feed_inputs(monkeypatch: pytest.MonkeyPatch, answers: list[str]) -> None:
    it: Iterator[str] = iter(answers)
    monkeypatch.setattr(builtins, "input", lambda *a: next(it))


def test_interact_quits(monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
                        capsys: pytest.CaptureFixture[str]) -> None:
    config = parse_config(_config(tmp_path, str(tmp_path / "m.txt")))
    maze, reserved = build_maze(config)
    # Toggle path -> change color -> auto regenerate -> regenerate with seed ->
    # quit, completing without exceptions.
    _feed_inputs(monkeypatch, ["3", "4", "1", "2", "123", "5"])
    interact(config, maze, reserved)
    out = capsys.readouterr().out
    assert "A-Maze-ing" in out


def test_interact_seed_input(monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
                             capsys: pytest.CaptureFixture[str]) -> None:
    config = parse_config(_config(tmp_path, str(tmp_path / "m.txt")))
    maze, reserved = build_maze(config)
    # Seed input: invalid value -> re-enter -> regenerate with a valid value ->
    # quit. Completes without exceptions.
    _feed_inputs(monkeypatch, ["2", "abc", "2", "42", "5"])
    interact(config, maze, reserved)
    # The specified seed is reflected in the configuration.
    assert config.options.seed == 42
    assert "Please enter an integer" in capsys.readouterr().out


def test_interact_handles_eof(monkeypatch: pytest.MonkeyPatch,
                              tmp_path: Path) -> None:
    config = parse_config(_config(tmp_path, str(tmp_path / "m.txt")))
    maze, reserved = build_maze(config)

    def raise_eof(*_a: object) -> str:
        raise EOFError

    monkeypatch.setattr(builtins, "input", raise_eof)
    interact(config, maze, reserved)  # returns immediately without hanging
