"""Imperfect-maze conversion (braiding) and passage-width enforcement.

When ``PERFECT=False``, the dead ends of a perfect maze (spanning tree) are
reduced to create loops (multiple paths). When opening a wall, it avoids
creating a **fully open 3x3 area**, so passages stay at most 2 cells wide.

A perfect maze has 1-cell-wide passages and satisfies this constraint
automatically, but braiding can widen them, so each wall removal is checked to
ensure it does not create a 3x3 open area.
"""

from __future__ import annotations

import random
from typing import List, Set, Tuple

from maze import DIRECTIONS, Maze

Coord = Tuple[int, int]


def _openings(maze: Maze, x: int, y: int) -> int:
    """Return the number of open walls (passages) of cell ``(x, y)``."""
    return sum(1 for d in DIRECTIONS if maze.is_open(x, y, d))


def _creates_open_3x3(maze: Maze, x: int, y: int) -> bool:
    """Return whether any 3x3 block containing ``(x, y)`` is fully open."""
    for tlx in range(max(0, x - 2), min(x, maze.width - 3) + 1):
        for tly in range(max(0, y - 2), min(y, maze.height - 3) + 1):
            if maze.is_open_area(tlx, tly, 3, 3):
                return True
    return False


def braid(maze: Maze, reserved: Set[Coord], rng: random.Random,
          ratio: float = 1.0) -> int:
    """Reduce dead ends to create loops, making the maze imperfect.

    For each dead end (a cell with a single opening), open one closed wall to
    connect it to another passage. Openings that create a 3x3 open area are not
    performed, and reserved cells ("42") are never connected to.

    Args:
        maze: The target maze (modified in place).
        reserved: Set of reserved cells ("42") that must not be touched.
        rng: Random source.
        ratio: Fraction of dead ends to process (0.0-1.0).

    Returns:
        The number of walls actually opened.
    """
    reserved = set(reserved)
    dead_ends: List[Coord] = [
        (x, y)
        for y in range(maze.height)
        for x in range(maze.width)
        if (x, y) not in reserved and _openings(maze, x, y) == 1
    ]
    rng.shuffle(dead_ends)
    target = int(len(dead_ends) * ratio)

    opened = 0
    for (x, y) in dead_ends[:target]:
        # A previous operation may have changed the opening count, so recheck.
        if _openings(maze, x, y) != 1:
            continue
        # Candidates: walls toward an in-bounds, non-reserved neighbor that
        # are currently closed.
        candidates = []
        for d, (dx, dy, bit) in DIRECTIONS.items():
            nx, ny = x + dx, y + dy
            if (maze.in_bounds(nx, ny) and (nx, ny) not in reserved
                    and maze.has_wall(x, y, bit)):
                candidates.append(d)
        rng.shuffle(candidates)

        for d in candidates:
            dx, dy, _ = DIRECTIONS[d]
            maze.open_wall(x, y, d)
            # Undo it if it creates a 3x3 open area.
            if _creates_open_3x3(maze, x, y) or \
                    _creates_open_3x3(maze, x + dx, y + dy):
                maze.close_wall(x, y, d)
            else:
                opened += 1
                break
    return opened
