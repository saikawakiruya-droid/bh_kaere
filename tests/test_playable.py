# [TEST FILE] 提出・採点対象外（仕様 III.3）— 動作確認専用。実行: make test / pytest
"""Tests for the playable Pac-Man board (spec IV.4, v2.2, PERFECT=False)."""

from __future__ import annotations

import random
from typing import Set, Tuple

import pytest

from a_maze_ing import PLAYABLE_MIN_LOOPS, _corridor_cells, build_maze
from config import Config, Options
from engine.backtracker import generate_backtracker
from engine.braiding import braid
from engine.initializer import reserved_cells
from engine.maze import Maze
from engine.metrics import count_dead_ends, count_loops
from engine.validator import validate

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


def _openings(maze: Maze, x: int, y: int) -> int:
    return sum(1 for d in ("N", "E", "S", "W") if maze.is_open(x, y, d))


# 30x12 seed=7 is the regression case: the "42" sign used to be placed so that
# it reserved three of the centre cell's four neighbours, leaving the centre a
# dead end that braiding could not repair.
@pytest.mark.parametrize("width,height,seed", [
    (25, 20, 42),
    (30, 12, 7),
    (20, 15, 1),
    (24, 14, 3),
    (12, 9, 5),
    (40, 10, 2),
])
def test_corners_and_centre_are_open_corridors(
        width: int, height: int, seed: int) -> None:
    cfg = _config(width, height, (0, 0), (width - 1, height - 1), seed)
    maze, reserved = build_maze(cfg)
    for (x, y) in _corridor_cells(cfg.width, cfg.height):
        assert (x, y) not in reserved
        assert maze.cells[y][x] != 0xF          # not fully closed
        # A through-corridor has at least two openings.
        assert _openings(maze, x, y) >= 2, (x, y, _openings(maze, x, y))


def test_sign_never_strangles_a_corridor_cell() -> None:
    """The sign must leave every corridor cell at least two free neighbours."""
    cfg = _config(30, 12, (0, 0), (29, 11), 7)
    _, reserved = build_maze(cfg)
    for (x, y) in _corridor_cells(cfg.width, cfg.height):
        free_neighbours = sum(
            1
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
            if 0 <= x + dx < cfg.width and 0 <= y + dy < cfg.height
            and (x + dx, y + dy) not in reserved
        )
        assert free_neighbours >= 2, (x, y, free_neighbours)


def test_validator_rejects_a_dead_end_centre() -> None:
    """A centre with a single opening must be reported (not silently accepted).

    Guards against the validator's playable check regressing to "not fully
    closed and reachable", which passed a dead-end centre.
    """
    cfg = _config(20, 15, (0, 0), (19, 14), 4)
    maze, reserved = build_maze(cfg)
    cx, cy = cfg.width // 2, cfg.height // 2
    # Wall the centre off until only one opening is left.
    while _openings(maze, cx, cy) > 1:
        for d in ("N", "E", "S", "W"):
            if maze.is_open(cx, cy, d) and _openings(maze, cx, cy) > 1:
                maze.close_wall(cx, cy, d)
    problems = validate(maze, cfg.entry, cfg.exit, reserved=reserved,
                        perfect=False, playable=True)
    assert any("dead end" in p and f"({cx},{cy})" in p for p in problems), \
        problems


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
