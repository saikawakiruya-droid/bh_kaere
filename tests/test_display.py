# [TEST FILE] 提出・採点対象外（仕様 III.3）— 動作確認専用。実行: make test / pytest
"""Unit tests for the display module (ASCII rendering and registry)."""

from __future__ import annotations

import pytest

from display import display_names, get_display_mode, render_ascii
from errors import ConfigValueError
from maze import Maze


def test_render_dimensions() -> None:
    maze = Maze(3, 2)  # all closed
    text = render_ascii(maze)
    lines = text.splitlines()
    # For height h, the number of lines = 2h + 1.
    assert len(lines) == 2 * 2 + 1
    # For width w, each line's length = 4w + 1.
    assert all(len(line) == 4 * 3 + 1 for line in lines)


def test_render_marks_entry_exit_and_sign() -> None:
    maze = Maze(3, 3)
    text = render_ascii(
        maze, entry=(0, 0), exit_=(2, 2), reserved={(1, 1)})
    assert " E " in text
    assert " X " in text
    assert "###" in text


def test_show_path_toggle() -> None:
    maze = Maze(3, 3)
    with_path = render_ascii(maze, path={(1, 1)}, show_path=True)
    without_path = render_ascii(maze, path={(1, 1)}, show_path=False)
    assert " * " in with_path
    assert " * " not in without_path


def test_wall_color_adds_ansi() -> None:
    maze = Maze(3, 2)
    plain = render_ascii(maze)
    colored = render_ascii(maze, wall_color="\033[31m")
    assert "\033[31m" not in plain     # default is uncolored
    assert "\033[31m" in colored       # colored output contains the ANSI code


def test_registry_has_ascii() -> None:
    assert "ascii" in display_names()
    assert get_display_mode("ascii") is render_ascii


def test_unknown_display_raises() -> None:
    with pytest.raises(ConfigValueError):
        get_display_mode("opengl")
