# [TEST FILE] 提出・採点対象外（仕様 III.3）— 動作確認専用。実行: make test / pytest
"""Tests for the playable Pac-Man board (spec IV.4, v2.2, PERFECT=False)."""

from __future__ import annotations

import random
from typing import Set, Tuple

import pytest

from a_maze_ing import PLAYABLE_MIN_LOOPS, _corridor_cells, build_maze
from braiding import braid, count_dead_ends, count_loops
from config import Config
from generator import generate_backtracker
from initializer import reserved_cells
from maze import Maze
from options import Options
from validator import validate

Coord = Tuple[int, int]


def _config(width: int, height: int, entry: Coord, exit_: Coord,
            seed: int, perfect: bool = False) -> Config:
    opts = Options(seed=seed, algorithm="backtracker", display="ascii",
                   sign="42")
    return Config(width=width, height=height, entry=entry, exit=exit_,
                  output_file="o.txt", perfect=perfect, options=opts)


def _perfect(width: int, height: int, seed: int) -> Tuple[Maze, Set[Coord]]:
    reserved = reserved_cells(width, height)
    maze = generate_backtracker(
        width, height, reserved, random.Random(seed), start=(0, 0))
    return maze, reserved


@pytest.mark.parametrize("seed", [1, 42, 7, 100])
def test_build_playable_passes_validation(seed: int) -> None:
    cfg = _config(25, 20, (0, 0), (24, 19), seed)
    maze, reserved = build_maze(cfg)
    problems = validate(maze, cfg.entry, cfg.exit, reserved=reserved,
                        perfect=False, playable=True)
    assert problems == [], problems


def test_corners_and_centre_are_open_corridors() -> None:
    cfg = _config(25, 20, (0, 0), (24, 19), 42)
    maze, reserved = build_maze(cfg)
    for (x, y) in _corridor_cells(cfg.width, cfg.height):
        assert (x, y) not in reserved
        assert maze.cells[y][x] != 0xF          # not fully closed
        # A through-corridor has at least two openings.
        openings = sum(1 for d in ("N", "E", "S", "W")
                       if maze.is_open(x, y, d))
        assert openings >= 2, (x, y, openings)


def test_at_least_two_independent_loops() -> None:
    cfg = _config(25, 20, (0, 0), (24, 19), 3)
    maze, reserved = build_maze(cfg)
    assert count_loops(maze, reserved) >= PLAYABLE_MIN_LOOPS


def test_dead_ends_stay_rare() -> None:
    cfg = _config(25, 20, (0, 0), (24, 19), 7)
    maze, reserved = build_maze(cfg)
    free = cfg.width * cfg.height - len(reserved)
    assert count_dead_ends(maze, reserved) <= max(4, free // 25)


def test_small_board_still_playable() -> None:
    # A small maze where the sign is omitted must still be a valid board.
    cfg = _config(8, 7, (0, 0), (7, 6), 2)
    maze, reserved = build_maze(cfg)
    problems = validate(maze, cfg.entry, cfg.exit, reserved=reserved,
                        perfect=False, playable=True)
    assert problems == [], problems


def test_perfect_maze_flagged_as_not_playable() -> None:
    # A plain perfect maze has 0 loops and many dead ends -> not playable.
    maze, reserved = _perfect(25, 20, seed=5)
    problems = validate(maze, (0, 0), (24, 19), reserved=reserved,
                        perfect=False, playable=True)
    assert any("loop" in p for p in problems)


def test_playable_is_reproducible() -> None:
    cfg1 = _config(20, 15, (0, 0), (19, 14), 11)
    cfg2 = _config(20, 15, (0, 0), (19, 14), 11)
    maze1, _ = build_maze(cfg1)
    maze2, _ = build_maze(cfg2)
    assert maze1.cells == maze2.cells


def test_braid_min_loops_guarantee() -> None:
    maze, reserved = _perfect(20, 15, seed=9)
    braid(maze, reserved, random.Random(1),
          corridors=_corridor_cells(20, 15), min_loops=PLAYABLE_MIN_LOOPS)
    assert count_loops(maze, reserved) >= PLAYABLE_MIN_LOOPS
