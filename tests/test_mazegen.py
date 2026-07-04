# [TEST FILE] 提出・採点対象外（仕様 III.3）— 動作確認専用。実行: make test / pytest
"""Unit tests for the reusable mazegen module (MazeGenerator)."""

from __future__ import annotations

from mazegen import MazeGenerator


def _carved_edges(gen: MazeGenerator) -> int:
    edges = 0
    for y in range(gen.height):
        for x in range(gen.width):
            for d in ("E", "S"):
                if gen._is_open(x, y, d):
                    edges += 1
    return edges


def test_generate_fills_grid_connected() -> None:
    gen = MazeGenerator(12, 8, seed=42).generate()
    dist = gen._distances((0, 0))
    assert len(dist) == 12 * 8  # all cells connected


def test_perfect_is_spanning_tree() -> None:
    gen = MazeGenerator(12, 8, seed=1).generate()
    assert _carved_edges(gen) == 12 * 8 - 1


def test_seed_reproducible() -> None:
    a = MazeGenerator(10, 10, seed=7).generate()
    b = MazeGenerator(10, 10, seed=7).generate()
    assert a.grid == b.grid


def test_different_seed_differs() -> None:
    a = MazeGenerator(10, 10, seed=1).generate()
    b = MazeGenerator(10, 10, seed=2).generate()
    assert a.grid != b.grid


def test_solution_walks_entry_to_exit() -> None:
    gen = MazeGenerator(12, 8, seed=3).generate()
    entry, exit_ = (0, 0), (11, 7)
    path = gen.solution(entry, exit_)
    assert path is not None
    # Following the path reaches the exit.
    x, y = entry
    moves = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}
    for step in path:
        assert gen._is_open(x, y, step)
        dx, dy = moves[step]
        x, y = x + dx, y + dy
    assert (x, y) == exit_


def test_solution_is_shortest() -> None:
    gen = MazeGenerator(12, 8, seed=4).generate()
    path = gen.solution((0, 0), (11, 7))
    assert path is not None
    assert len(path) == gen._distances((0, 0))[(11, 7)]


def test_solution_cells_count() -> None:
    gen = MazeGenerator(12, 8, seed=4).generate()
    path = gen.solution((0, 0), (11, 7))
    cells = gen.solution_cells((0, 0), (11, 7))
    assert path is not None
    assert len(cells) == len(path) + 1


def test_imperfect_has_loops() -> None:
    perfect = MazeGenerator(20, 15, seed=9, perfect=True).generate()
    braided = MazeGenerator(20, 15, seed=9, perfect=False).generate()
    assert _carved_edges(braided) > _carved_edges(perfect)


def test_entry_equals_exit_empty() -> None:
    gen = MazeGenerator(5, 5, seed=1).generate()
    assert gen.solution((2, 2), (2, 2)) == ""


def test_wall_code_access() -> None:
    gen = MazeGenerator(5, 5, seed=1).generate()
    assert 0 <= gen.wall_code(0, 0) <= 0xF
