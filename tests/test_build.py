# [TEST FILE] 提出・採点対象外（仕様 III.3）— 動作確認専用。実行: make test / pytest
"""Unit tests for engine.build (sign reservation, generation, braiding)."""

from __future__ import annotations

import random
from typing import Set, Tuple

import pytest

from engine.build import (
    GLYPH_HEIGHT,
    _openings,
    algorithm_names,
    braid,
    generate_backtracker,
    get_algorithm,
    initialize_maze,
    reserved_cells,
    sign_bitmap,
)
from engine.errors import ConfigValueError, SignOverlapError, SignTooBigError
from engine.maze import DIRECTIONS, Maze, bfs_distances
from engine.validator import validate

Coord = Tuple[int, int]


# ===========================================================================
# Sign reservation and initial maze (formerly test_initializer.py)
# ===========================================================================


def test_bitmap_dimensions() -> None:
    bitmap = sign_bitmap("42")
    assert len(bitmap) == GLYPH_HEIGHT
    # 3 + gap(1) + 3 = 7
    assert all(len(row) == 7 for row in bitmap)


def test_bitmap_gap() -> None:
    # Gap 1 (default) is width 7, gap 2 is width 8. Height is always fixed.
    assert all(len(r) == 7 for r in sign_bitmap("42", gap=1))
    assert all(len(r) == 8 for r in sign_bitmap("42", gap=2))


def test_gap_out_of_range_rejected() -> None:
    with pytest.raises(ValueError):
        sign_bitmap("42", gap=3)


def test_unknown_glyph_raises() -> None:
    with pytest.raises(KeyError):
        sign_bitmap("9")


def test_reserved_cells_centered_and_in_bounds() -> None:
    w, h = 20, 15
    cells = reserved_cells(w, h)
    assert len(cells) > 0
    assert all(0 <= x < w and 0 <= y < h for x, y in cells)


def test_reserved_cell_count_matches_ones() -> None:
    bitmap = sign_bitmap("42")
    ones = sum(row.count("1") for row in bitmap)
    assert len(reserved_cells(20, 15)) == ones


def test_too_small_raises() -> None:
    with pytest.raises(SignTooBigError):
        reserved_cells(6, 6)


def test_overlap_relocates_when_room() -> None:
    # Even if a centered cell is passed in avoid, it relocates to a
    # non-overlapping position when there is room (does not error).
    centered = reserved_cells(20, 15)
    a_sign_cell = next(iter(centered))
    moved = reserved_cells(20, 15, avoid={a_sign_cell})
    assert len(moved) == len(centered)
    assert a_sign_cell not in moved


def test_cannot_place_when_not_generatable() -> None:
    # The frame (7x7) fits, but the "2" notch gets trapped at the right edge
    # and no generatable placement exists, so SignOverlapError is raised.
    with pytest.raises(SignOverlapError):
        reserved_cells(7, 7)


def test_smallest_generatable_is_8x6() -> None:
    # The minimum size 8x6 is placeable. All free cells stay connected.
    cells = reserved_cells(8, 6)
    assert len(cells) > 0
    free = {(x, y) for y in range(6) for x in range(8) if (x, y) not in cells}
    # The free cells are connected (guaranteeing generatability).
    start = next(iter(free))
    seen, stack = {start}, [start]
    while stack:
        x, y = stack.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy)
            if n in free and n not in seen:
                seen.add(n)
                stack.append(n)
    assert seen == free


def test_endpoints_decide_sign_at_same_size() -> None:
    # Even at the same size 8x7, the entry/exit coords decide placeable or not.
    placed = reserved_cells(8, 7, avoid={(0, 6), (7, 0)})
    assert len(placed) > 0
    # (0,1) is a cell common to every valid placement -> nowhere to put it,
    # so it is omitted.
    with pytest.raises(SignOverlapError):
        reserved_cells(8, 7, avoid={(0, 1), (7, 6)})


def test_no_overlap_when_endpoints_far() -> None:
    # Corners do not overlap the centered sign.
    cells = reserved_cells(20, 15, avoid={(0, 0), (19, 14)})
    assert (0, 0) not in cells and (19, 14) not in cells


def test_too_small_and_overlap_are_distinct() -> None:
    # The two sign errors are distinguishable as separate classes.
    assert not issubclass(SignTooBigError, SignOverlapError)
    assert not issubclass(SignOverlapError, SignTooBigError)


def test_default_gap_is_one() -> None:
    # Auto-selection uses gap 1 by default (width 7).
    cells = reserved_cells(20, 15)
    xs = {x for x, _ in cells}
    assert max(xs) - min(xs) + 1 == 7  # 3+1+3 = 7


def test_explicit_gap_too_wide_rejected() -> None:
    with pytest.raises(ValueError):
        reserved_cells(20, 15, gap=3)  # 3+ is too far apart


def test_explicit_gap_two_allowed() -> None:
    cells = reserved_cells(20, 15, gap=2)
    xs = {x for x, _ in cells}
    assert max(xs) - min(xs) + 1 == 8  # 3+2+3 = 8


def test_frame_too_small_raises_toobig() -> None:
    # Width 6 does not fit the frame at any gap -> SignTooBigError.
    with pytest.raises(SignTooBigError):
        reserved_cells(6, 15)
    # Height 4 also does not fit the frame.
    with pytest.raises(SignTooBigError):
        reserved_cells(20, 4)


def test_initialize_maze_all_closed_and_reserved() -> None:
    maze, reserved = initialize_maze(20, 15, entry=(0, 0), exit_=(19, 14))
    # Every cell is initialized walled on all four sides (0xF).
    assert all(cell == 0xF for row in maze.cells for cell in row)
    assert len(reserved) > 0


def test_initialize_maze_omits_sign_when_frame_too_small(
        capsys: pytest.CaptureFixture[str]) -> None:
    maze, reserved = initialize_maze(6, 6, entry=(0, 0), exit_=(5, 5))
    assert reserved == set()
    assert "does not fit" in capsys.readouterr().out


def test_initialize_maze_relocates_sign_on_overlap() -> None:
    # Even with the entry near the center, it relocates to a non-overlapping
    # position when there is room.
    maze, reserved = initialize_maze(20, 15, entry=(10, 7), exit_=(0, 0))
    assert len(reserved) > 0
    assert (10, 7) not in reserved
    assert (0, 0) not in reserved


def test_initialize_maze_omits_sign_when_not_generatable(
        capsys: pytest.CaptureFixture[str]) -> None:
    # 7x7 fits the frame but has no generatable placement, so it is omitted.
    maze, reserved = initialize_maze(7, 7, entry=(0, 0), exit_=(6, 6))
    assert reserved == set()
    assert "cannot place" in capsys.readouterr().out


# ===========================================================================
# Generation algorithms (formerly test_generator.py)
# ===========================================================================


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


# ===========================================================================
# Braiding / imperfect-maze conversion (formerly test_braiding.py)
# ===========================================================================


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
    before = sum(1 for c in free if _openings(maze, *c) == 1)
    braid(maze, reserved, random.Random(2))
    after = sum(1 for c in free if _openings(maze, *c) == 1)
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
