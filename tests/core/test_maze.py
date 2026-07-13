# [TEST FILE] 提出・採点対象外（仕様 III.3）— 動作確認専用。実行: make test / pytest
"""Unit tests for the maze module's search algorithms."""

from __future__ import annotations

from typing import List

import pytest

from core.maze import (
    WALL_E,
    WALL_N,
    WALL_S,
    WALL_W,
    Maze,
    bfs_distances,
    path_to_cells,
    solution_cells,
    solve,
)


def _open_grid(width: int, height: int) -> List[List[int]]:
    """Build a grid with all internal walls open (only the border closed)."""
    cells = [[0 for _ in range(width)] for _ in range(height)]
    for y in range(height):
        for x in range(width):
            code = 0
            if y == 0:
                code |= WALL_N
            if y == height - 1:
                code |= WALL_S
            if x == 0:
                code |= WALL_W
            if x == width - 1:
                code |= WALL_E
            cells[y][x] = code
    return cells


def test_entry_equals_exit_returns_empty() -> None:
    maze = Maze(3, 3, _open_grid(3, 3))
    assert solve(maze, (1, 1), (1, 1)) == ""


def test_straight_corridor() -> None:
    # A single-row corridor. (0,0) -> (2,0) is "EE".
    cells = _open_grid(3, 1)
    maze = Maze(3, 1, cells)
    assert solve(maze, (0, 0), (2, 0)) == "EE"


def test_shortest_path_on_open_grid() -> None:
    # On a fully open grid, the shortest step count = Manhattan distance.
    maze = Maze(4, 4, _open_grid(4, 4))
    path = solve(maze, (0, 0), (3, 3))
    assert path is not None
    assert len(path) == 6
    assert path.count("E") == 3
    assert path.count("S") == 3


def test_unreachable_returns_none() -> None:
    # 2x1 with the middle wall closed, splitting the two cells.
    cells = _open_grid(2, 1)
    cells[0][0] |= WALL_E
    cells[0][1] |= WALL_W
    maze = Maze(2, 1, cells)
    assert solve(maze, (0, 0), (1, 0)) is None


def test_wall_consistency_blocks_move() -> None:
    maze = Maze(2, 1, _open_grid(2, 1))
    # Close the adjacent wall from both sides.
    maze.cells[0][0] |= WALL_E
    maze.cells[0][1] |= WALL_W
    assert maze.is_open(0, 0, "E") is False
    assert maze.is_open(1, 0, "W") is False


def test_out_of_bounds_raises() -> None:
    maze = Maze(3, 3, _open_grid(3, 3))
    with pytest.raises(ValueError):
        solve(maze, (-1, 0), (2, 2))
    with pytest.raises(ValueError):
        solve(maze, (0, 0), (3, 3))


def test_bfs_distances_open_grid() -> None:
    maze = Maze(3, 3, _open_grid(3, 3))
    dist = bfs_distances(maze, (0, 0))
    assert dist[(0, 0)] == 0
    assert dist[(2, 2)] == 4  # Manhattan distance
    assert len(dist) == 9     # all cells reachable


def test_bfs_distances_excludes_unreachable() -> None:
    cells = _open_grid(2, 1)
    cells[0][0] |= WALL_E
    cells[0][1] |= WALL_W
    maze = Maze(2, 1, cells)
    dist = bfs_distances(maze, (0, 0))
    assert (1, 0) not in dist


def test_solution_cells_on_straight_corridor() -> None:
    maze = Maze(3, 1, _open_grid(3, 1))
    assert solution_cells(maze, (0, 0), (2, 0)) == {(0, 0), (1, 0), (2, 0)}


def test_solution_cells_count_matches_path_length() -> None:
    # L-shaped path: path length 2 -> 3 cells.
    cells = _open_grid(2, 2)
    cells[0][0] |= WALL_E
    cells[0][1] |= WALL_W
    cells[0][1] |= WALL_S
    cells[1][1] |= WALL_N
    maze = Maze(2, 2, cells)
    path = solve(maze, (0, 0), (1, 1))
    cells_on = solution_cells(maze, (0, 0), (1, 1))
    assert path is not None
    assert len(cells_on) == len(path) + 1


def test_solution_cells_unreachable_empty() -> None:
    cells = _open_grid(2, 1)
    cells[0][0] |= WALL_E
    cells[0][1] |= WALL_W
    maze = Maze(2, 1, cells)
    assert solution_cells(maze, (0, 0), (1, 0)) == set()


def test_solved_path_is_walkable() -> None:
    # L-shape: only (0,0)->(0,1)->(1,1) is passable.
    cells = _open_grid(2, 2)
    # Close between (0,0) and (1,0).
    cells[0][0] |= WALL_E
    cells[0][1] |= WALL_W
    # Close between (1,0) and (1,1).
    cells[0][1] |= WALL_S
    cells[1][1] |= WALL_N
    maze = Maze(2, 2, cells)
    assert solve(maze, (0, 0), (1, 1)) == "SE"


def test_path_to_cells_traces_single_path() -> None:
    # The move string is walked from the entry into exactly len+1 cells.
    assert path_to_cells((0, 0), "SE") == {(0, 0), (0, 1), (1, 1)}
    assert path_to_cells((2, 3), "") == {(2, 3)}


def test_path_to_cells_is_one_path_within_all_shortest() -> None:
    # Fully open 3x3 grid: many shortest paths (0,0)->(2,2) exist.
    maze = Maze(3, 3, _open_grid(3, 3))
    entry, exit_ = (0, 0), (2, 2)
    sol = solve(maze, entry, exit_)
    assert sol is not None
    single = path_to_cells(entry, sol)
    union = solution_cells(maze, entry, exit_)
    # The single traced path has exactly len(sol)+1 cells and is a subset of
    # the union of every shortest path (which is strictly larger here).
    assert len(single) == len(sol) + 1
    assert single < union
