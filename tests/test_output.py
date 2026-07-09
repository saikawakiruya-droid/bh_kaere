# [TEST FILE] 提出・採点対象外（仕様 III.3）— 動作確認専用。実行: make test / pytest
"""Unit tests for engine.output (file writing and terminal display)."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.errors import ConfigValueError
from engine.maze import WALL_E, WALL_N, WALL_S, WALL_W, Maze
from engine.output import (
    display_names,
    format_maze,
    get_display_mode,
    render_ascii,
    write_maze,
)


# ===========================================================================
# File output (formerly test_writer.py)
# ===========================================================================


def test_hex_encoding_matches_wall_bits() -> None:
    # Corner cell (0,0) is closed on north and west -> 1001b = 9.
    maze = Maze(2, 1)
    maze.cells[0][0] = WALL_N | WALL_W           # 1001 = 9
    maze.cells[0][1] = WALL_N | WALL_E | WALL_S  # 0111 = 7
    text = format_maze(maze, (0, 0), (1, 0), "E")
    first = text.splitlines()[0]
    assert first == "97"


def test_structure_and_trailing_newlines() -> None:
    maze = Maze(3, 2)
    text = format_maze(maze, (0, 0), (2, 1), "ESE")
    lines = text.split("\n")
    # The last entry is "" (the final line is also \n-terminated).
    assert lines[-1] == ""
    body = lines[:-1]
    # 2 hex rows + blank line + entry + exit + path = 5 lines.
    assert len(body) == 2 + 1 + 3
    assert body[2] == ""              # blank line
    assert body[3] == "0,0"           # entry x,y
    assert body[4] == "2,1"           # exit x,y
    assert body[5] == "ESE"           # path


def test_all_walls_closed_is_F() -> None:
    maze = Maze(3, 1)  # all closed 0xF by default
    text = format_maze(maze, (0, 0), (2, 0), "EE")
    assert text.splitlines()[0] == "FFF"


def test_none_solution_writes_blank_line() -> None:
    maze = Maze(2, 1)
    text = format_maze(maze, (0, 0), (1, 0), None)
    assert text.split("\n")[:-1][-1] == ""  # the path line is blank


def test_write_maze_uses_lf_newlines(tmp_path: Path) -> None:
    maze = Maze(2, 2)
    out = tmp_path / "maze.txt"
    write_maze(str(out), maze, (0, 0), (1, 1), "SE")
    raw = out.read_bytes()
    # LF only, not converted to CRLF.
    assert b"\r\n" not in raw
    assert raw.endswith(b"\n")


def test_write_then_read_roundtrip(tmp_path: Path) -> None:
    maze = Maze(4, 3)
    out = tmp_path / "m.txt"
    write_maze(str(out), maze, (0, 0), (3, 2), "EEESS")
    content = out.read_text(encoding="utf-8")
    assert content == format_maze(maze, (0, 0), (3, 2), "EEESS")


# ===========================================================================
# Terminal display (formerly test_display.py)
# ===========================================================================


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
