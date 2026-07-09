# [TEST FILE] 提出・採点対象外（仕様 III.3）— 動作確認専用。実行: make test / pytest
"""Unit tests for the validator module (maze condition checks)."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Set, Tuple

from engine.build import generate_backtracker, reserved_cells
from engine.maze import WALL_E, WALL_N, WALL_S, WALL_W, Maze, solve
from engine.output import write_maze
from engine.validator import _parse_output_file, main, validate

Coord = Tuple[int, int]


def _generated(width: int = 20, height: int = 15,
               seed: int = 42) -> Tuple[Maze, Set[Coord]]:
    reserved = reserved_cells(width, height)
    maze = generate_backtracker(
        width, height, reserved, random.Random(seed), start=(0, 0))
    return maze, reserved


def test_generated_maze_is_valid() -> None:
    # Confirm all conditions hold after generation (perfect + 42 + solution).
    maze, reserved = _generated()
    entry, exit_ = (0, 0), (19, 14)
    solution = solve(maze, entry, exit_)
    problems = validate(maze, entry, exit_, reserved=reserved,
                        perfect=True, solution=solution)
    assert problems == [], problems


def test_detects_missing_border() -> None:
    maze, reserved = _generated()
    maze.cells[0][5] &= ~WALL_N  # open the north border wall
    problems = validate(maze, (0, 0), (19, 14), reserved=reserved)
    assert any("border" in p for p in problems)


def test_detects_wall_inconsistency() -> None:
    maze = Maze(2, 1)
    maze.cells[0][0] &= ~WALL_E  # open only one side -> mismatch
    problems = validate(maze, (0, 0), (1, 0))
    assert any("wall mismatch" in p for p in problems)


def test_detects_isolated_cell() -> None:
    # 4x1: (0,0)-(1,0) are the entry side, (2,0)-(3,0) a disconnected isolated
    # component. No cell is 0xF (i.e. real isolation, not the 42 exception).
    maze = Maze(4, 1, [[0xD, 0x7, 0xD, 0x7]])
    problems = validate(maze, (0, 0), (3, 0))
    assert any("isolated" in p for p in problems)


def test_detects_open_3x3() -> None:
    # Fully open the internal walls of a 3x3 -> open area. Border stays closed.
    maze = Maze(3, 3, [[0 for _ in range(3)] for _ in range(3)])
    for y in range(3):
        for x in range(3):
            code = 0
            if y == 0:
                code |= WALL_N
            if y == 2:
                code |= WALL_S
            if x == 0:
                code |= WALL_W
            if x == 2:
                code |= WALL_E
            maze.cells[y][x] = code
    problems = validate(maze, (0, 0), (2, 2))
    assert any("3x3" in p for p in problems)


def test_detects_bad_solution() -> None:
    maze, reserved = _generated()
    problems = validate(maze, (0, 0), (19, 14), reserved=reserved,
                        solution="NNNN")  # invalid path through walls
    assert any("path" in p for p in problems)


def test_detects_non_perfect_when_cycle() -> None:
    # Open all of a 2x2 to create a loop -> not a perfect maze.
    cells = [[0, 0], [0, 0]]
    maze = Maze(2, 2, cells)
    for y in range(2):
        for x in range(2):
            code = 0
            if y == 0:
                code |= WALL_N
            if y == 1:
                code |= WALL_S
            if x == 0:
                code |= WALL_W
            if x == 1:
                code |= WALL_E
            maze.cells[y][x] = code
    problems = validate(maze, (0, 0), (1, 1), perfect=True)
    assert any("not a perfect maze" in p for p in problems)


def test_cli_roundtrip_ok(tmp_path: Path) -> None:
    maze, reserved = _generated()
    entry, exit_ = (0, 0), (19, 14)
    solution = solve(maze, entry, exit_)
    out = tmp_path / "maze.txt"
    write_maze(str(out), maze, entry, exit_, solution)
    # Read the output file back and validate OK.
    rmaze, rentry, rexit, rpath = _parse_output_file(str(out))
    assert validate(rmaze, rentry, rexit, solution=rpath) == []
    assert main([str(out)]) == 0
