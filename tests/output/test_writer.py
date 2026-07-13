# [TEST FILE] 提出・採点対象外（仕様 III.3）— 動作確認専用。実行: make test / pytest
"""Unit tests for the writer module (output-file format)."""

from __future__ import annotations

from pathlib import Path

from core.maze import WALL_E, WALL_N, WALL_S, WALL_W, Maze
from output.writer import format_maze, write_maze


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
