# [TEST FILE] 提出・採点対象外（仕様 III.3）— 動作確認専用。実行: make test / pytest
"""Unit tests for the braiding module (imperfect-maze conversion)."""

from __future__ import annotations

import random
from typing import Set, Tuple

from engine.backtracker import generate_backtracker
from engine.braiding import braid
from engine.initializer import reserved_cells
from engine.maze import Maze, bfs_distances
from engine.validator import validate

Coord = Tuple[int, int]


def _perfect(width: int = 20, height: int = 15,
             seed: int = 5) -> Tuple[Maze, Set[Coord]]:
    reserved = reserved_cells(width, height)
    maze = generate_backtracker(
        width, height, reserved, random.Random(seed), start=(0, 0))
    return maze, reserved


def _open_edges(maze: Maze, reserved: Set[Coord]) -> int:
    edges = 0
    for y in range(maze.height):
        for x in range(maze.width):
            if (x, y) in reserved:
                continue
            for d in ("E", "S"):
                if maze.is_open(x, y, d):
                    edges += 1
    return edges


def test_braiding_adds_loops() -> None:
    maze, reserved = _perfect()
    before = _open_edges(maze, reserved)
    opened = braid(maze, reserved, random.Random(1))
    after = _open_edges(maze, reserved)
    assert opened > 0
    assert after == before + opened  # more edges = loops created


def test_braiding_reduces_dead_ends() -> None:
    maze, reserved = _perfect()
    free = [(x, y) for y in range(maze.height) for x in range(maze.width)
            if (x, y) not in reserved]
    before = sum(1 for c in free if maze.count_openings(*c) == 1)
    braid(maze, reserved, random.Random(2))
    after = sum(1 for c in free if maze.count_openings(*c) == 1)
    assert after < before


def test_braiding_keeps_connectivity_and_no_3x3() -> None:
    maze, reserved = _perfect()
    braid(maze, reserved, random.Random(3))
    # Connectivity kept, no 3x3 opening, borders, etc. (all non-perfect rules).
    problems = validate(maze, (0, 0), (19, 14), reserved=reserved,
                        perfect=False)
    assert problems == [], problems


def test_braiding_never_creates_open_3x3() -> None:
    maze, reserved = _perfect(30, 20, seed=9)
    braid(maze, reserved, random.Random(4))
    for y in range(maze.height - 2):
        for x in range(maze.width - 2):
            assert not maze.is_open_area(x, y, 3, 3)


def test_braiding_keeps_reserved_closed() -> None:
    maze, reserved = _perfect()
    braid(maze, reserved, random.Random(5))
    assert all(maze.cells[y][x] == 0xF for (x, y) in reserved)


def test_braiding_reproducible() -> None:
    m1, r1 = _perfect(seed=7)
    m2, r2 = _perfect(seed=7)
    braid(m1, r1, random.Random(11))
    braid(m2, r2, random.Random(11))
    assert m1.cells == m2.cells


def test_braided_maze_not_perfect() -> None:
    # After braiding it is no longer a spanning tree (edges > free cells - 1)
    # -> it fails the perfect check.
    maze, reserved = _perfect()
    braid(maze, reserved, random.Random(13))
    problems = validate(maze, (0, 0), (19, 14), reserved=reserved,
                        perfect=True)
    assert any("not a perfect maze" in p for p in problems)
    # Connectivity is preserved, so there is no isolation.
    free = {(x, y) for y in range(maze.height) for x in range(maze.width)
            if (x, y) not in reserved}
    assert set(bfs_distances(maze, (0, 0)).keys()) >= free
