# [TEST FILE] 提出・採点対象外（仕様 III.3）— 動作確認専用。実行: make test / pytest
"""Unit tests for the backtracker algorithm and the generator registry."""

from __future__ import annotations

import random
from typing import Set, Tuple

import pytest

from engine.backtracker import generate_backtracker
from engine.errors import ConfigValueError
from engine.generator import algorithm_names, get_algorithm
from engine.initializer import reserved_cells
from engine.maze import DIRECTIONS, Maze, bfs_distances

Coord = Tuple[int, int]


def _carved_edges(maze: Maze) -> int:
    """Count the number of open walls (passages)."""
    count = 0
    for y in range(maze.height):
        for x in range(maze.width):
            for direction in ("E", "S"):  # count only east/south to avoid dupes
                if maze.is_open(x, y, direction):
                    count += 1
    return count


def _free_cells(width: int, height: int, reserved: Set[Coord]) -> Set[Coord]:
    return {(x, y) for y in range(height) for x in range(width)
            if (x, y) not in reserved}


def test_all_free_cells_connected() -> None:
    rng = random.Random(1)
    reserved = reserved_cells(20, 15)
    maze = generate_backtracker(20, 15, reserved, rng, start=(0, 0))
    dist = bfs_distances(maze, (0, 0))
    free = _free_cells(20, 15, reserved)
    # Every free cell is reachable from the entry (no isolation).
    assert set(dist.keys()) == free


def test_reserved_cells_stay_fully_walled() -> None:
    rng = random.Random(2)
    reserved = reserved_cells(20, 15)
    maze = generate_backtracker(20, 15, reserved, rng, start=(0, 0))
    # Reserved cells stay 0xF (forming the 42 sign).
    assert all(maze.cells[y][x] == 0xF for (x, y) in reserved)


def test_perfect_maze_is_spanning_tree() -> None:
    rng = random.Random(3)
    reserved = reserved_cells(20, 15)
    maze = generate_backtracker(20, 15, reserved, rng, start=(0, 0))
    free = _free_cells(20, 15, reserved)
    # Spanning tree: edges = vertices - 1.
    assert _carved_edges(maze) == len(free) - 1


def test_seed_reproducibility() -> None:
    reserved = reserved_cells(20, 15)
    m1 = generate_backtracker(20, 15, reserved, random.Random(42), (0, 0))
    m2 = generate_backtracker(20, 15, reserved, random.Random(42), (0, 0))
    assert m1.cells == m2.cells


def test_different_seeds_differ() -> None:
    reserved = reserved_cells(20, 15)
    m1 = generate_backtracker(20, 15, reserved, random.Random(1), (0, 0))
    m2 = generate_backtracker(20, 15, reserved, random.Random(2), (0, 0))
    assert m1.cells != m2.cells


def test_no_reserved_connects_all() -> None:
    rng = random.Random(7)
    maze = generate_backtracker(8, 8, set(), rng, start=(0, 0))
    dist = bfs_distances(maze, (0, 0))
    assert len(dist) == 64


def test_registry_has_backtracker() -> None:
    assert "backtracker" in algorithm_names()
    assert get_algorithm("backtracker") is generate_backtracker


def test_unknown_algorithm_raises() -> None:
    with pytest.raises(ConfigValueError):
        get_algorithm("does-not-exist")


def test_wall_consistency_after_generation() -> None:
    # Adjacent cells' shared walls agree (east-open <-> west-open).
    rng = random.Random(9)
    maze = generate_backtracker(10, 10, set(), rng, start=(0, 0))
    for y in range(maze.height):
        for x in range(maze.width):
            for direction, (dx, dy, _) in DIRECTIONS.items():
                nx, ny = x + dx, y + dy
                if maze.in_bounds(nx, ny):
                    opp = {"N": "S", "S": "N", "E": "W", "W": "E"}[direction]
                    assert (maze.is_open(x, y, direction)
                            == maze.is_open(nx, ny, opp))
