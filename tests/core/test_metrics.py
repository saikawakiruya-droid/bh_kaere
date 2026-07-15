# [TEST FILE] 提出・採点対象外（仕様 III.3）— 動作確認専用。実行: make test / pytest
"""Unit tests pinning the expected values of core.metrics.

``count_loops`` and ``count_dead_ends`` are the core queries used by both
``braiding`` and ``verification.verifier``, so their return values are pinned
here directly on small hand-built mazes rather than only exercised indirectly
through generation. All mazes start fully closed (every cell ``0xF``) and are
carved open with :meth:`Maze.open_wall`, so the structure is explicit.
"""

from __future__ import annotations

from typing import Set, Tuple

from core.maze import Maze
from core.metrics import count_dead_ends, count_loops

Coord = Tuple[int, int]
NO_RESERVED: Set[Coord] = set()


def _corridor(length: int) -> Maze:
    """A single-row maze with every cell joined into one straight corridor."""
    maze = Maze(length, 1)
    for x in range(length - 1):
        maze.open_wall(x, 0, "E")
    return maze


def _open_ring_3x3() -> Maze:
    """A 3x3 maze open only around the border cells (the centre stays closed)."""
    maze = Maze(3, 3)
    ring = [(0, 0), (1, 0), (2, 0), (2, 1), (2, 2), (1, 2), (0, 2), (0, 1)]
    for (x, y), (nx, ny) in zip(ring, ring[1:] + ring[:1]):
        direction = {(1, 0): "E", (-1, 0): "W",
                     (0, 1): "S", (0, -1): "N"}[(nx - x, ny - y)]
        maze.open_wall(x, y, direction)
    return maze


# --------------------------------------------------------------------------- #
# count_loops
# --------------------------------------------------------------------------- #
def test_loops_spanning_tree_is_zero() -> None:
    # A straight corridor is a tree (edges = vertices - 1): no loops.
    assert count_loops(_corridor(3), NO_RESERVED) == 0


def test_loops_single_extra_edge_is_one() -> None:
    # A 2x2 fully open cell block has 4 edges over 4 vertices: exactly 1 loop.
    maze = Maze(2, 2)
    maze.open_wall(0, 0, "E")
    maze.open_wall(0, 0, "S")
    maze.open_wall(1, 0, "S")
    maze.open_wall(0, 1, "E")
    assert count_loops(maze, NO_RESERVED) == 1


def test_loops_fully_open_3x3_is_four() -> None:
    # 12 internal passages over 9 vertices -> 12 - 9 + 1 = 4 independent loops.
    maze = Maze(3, 3)
    for y in range(3):
        for x in range(3):
            if x + 1 < 3:
                maze.open_wall(x, y, "E")
            if y + 1 < 3:
                maze.open_wall(x, y, "S")
    assert count_loops(maze, NO_RESERVED) == 4


def test_loops_excludes_reserved_ring() -> None:
    # The 8 border cells form a ring (1 loop); the reserved centre and every
    # edge touching it are excluded from the count.
    assert count_loops(_open_ring_3x3(), {(1, 1)}) == 1


def test_loops_empty_when_all_reserved() -> None:
    maze = Maze(2, 2)
    assert count_loops(maze, {(0, 0), (1, 0), (0, 1), (1, 1)}) == 0


# --------------------------------------------------------------------------- #
# count_dead_ends
# --------------------------------------------------------------------------- #
def test_dead_ends_corridor_ends_count() -> None:
    # A 3-cell corridor: both end cells have a single opening and their other
    # sides are the outer border (a wall), so both are real dead ends.
    assert count_dead_ends(_corridor(3), NO_RESERVED) == 2


def test_dead_ends_none_when_every_cell_has_two_openings() -> None:
    # A 2x2 ring: each cell has two openings, so there are no dead ends.
    maze = Maze(2, 2)
    maze.open_wall(0, 0, "E")
    maze.open_wall(0, 0, "S")
    maze.open_wall(1, 0, "S")
    maze.open_wall(0, 1, "E")
    assert count_dead_ends(maze, NO_RESERVED) == 0


def test_dead_ends_border_counts_as_wall() -> None:
    # (0,0) opens only east; its north/west/south are the border. Border is a
    # wall, so (0,0) is a real dead end.
    maze = Maze(2, 1)
    maze.open_wall(0, 0, "E")
    assert count_dead_ends(maze, NO_RESERVED) == 2


def test_dead_ends_sign_adjacent_excluded() -> None:
    # Corridor (0,0)-(1,0) open; (2,0) is a reserved "42" cell. (1,0) has one
    # opening (west) and its east wall faces the sign, so the sign -- not a
    # wall -- is what closes it: (1,0) is NOT counted. Only (0,0) (closed by
    # the border) remains a real dead end.
    maze = Maze(3, 1)
    maze.open_wall(0, 0, "E")
    reserved = {(2, 0)}
    assert count_dead_ends(maze, reserved) == 1


def test_dead_ends_fully_sign_enclosed_is_zero() -> None:
    # A single free cell whose only closed neighbour in bounds is a sign has no
    # opening at all here; a cell reachable solely past a sign is never a real
    # dead end. With one opening toward another free cell and the rest sign or
    # border, the sign side keeps it from counting.
    maze = Maze(2, 2)
    # Open (0,0)-(0,1) only; reserve the whole right column as a sign.
    maze.open_wall(0, 0, "S")
    reserved = {(1, 0), (1, 1)}
    # (0,0): one opening (south), east faces sign, north/west border -> excluded.
    # (0,1): one opening (north), east faces sign, south/west border -> excluded.
    assert count_dead_ends(maze, reserved) == 0
