"""Structural metrics of a maze: independent loops and dead ends.

Both metrics are read-only queries over an already-built
:class:`~core.maze.Maze`.

Standalone usage::

    from core.metrics import count_loops, count_dead_ends

    loops = count_loops(maze, reserved=set())
    dead_ends = count_dead_ends(maze, reserved=set())
"""

from __future__ import annotations

from typing import Set, Tuple

from core.maze import DIRECTIONS, Maze

Coord = Tuple[int, int]


def count_loops(maze: Maze, reserved: Set[Coord]) -> int:
    """Return the number of independent loops among the free (non-reserved) cells.

    For a connected graph the cycle rank (number of independent loops) is
    ``edges - vertices + 1``.

    Args:
        maze: The maze to inspect.
        reserved: Set of reserved cells ("42") to exclude.

    Returns:
        The number of independent loops (``>= 0``).
    """
    vertices = 0
    edges = 0
    for y in range(maze.height):
        for x in range(maze.width):
            if (x, y) in reserved:
                continue
            vertices += 1
            for d in ("E", "S"):
                dx, dy, _ = DIRECTIONS[d]
                if (x + dx, y + dy) in reserved:
                    continue
                if maze.is_open(x, y, d):
                    edges += 1
    if vertices == 0:
        return 0
    return edges - vertices + 1


def count_dead_ends(maze: Maze, reserved: Set[Coord]) -> int:
    """Return the number of *real* dead ends among the free (non-reserved) cells.

    A cell is a dead end when it has exactly one opening. For this check the
    outer border counts as a wall, but a reserved ("42") cell does *not*: a wall
    facing a sign cell is not treated as a wall here. As a result, no cell is
    reported as a dead end merely because the sign blocks its other sides.

    Args:
        maze: The maze to inspect.
        reserved: Set of reserved cells ("42") to exclude.

    Returns:
        The number of real dead ends (``>= 0``).
    """
    real = 0
    for y in range(maze.height):
        for x in range(maze.width):
            if (x, y) in reserved or maze.count_openings(x, y) != 1:
                continue
            # Border walls count, but a sign does not: if any wall faces a
            # reserved cell, that side is closed by the sign (not a wall), so
            # this is not a genuine dead end.
            touches_sign = any(
                maze.has_wall(x, y, wall_bit)
                and maze.in_bounds(x + dx, y + dy)
                and (x + dx, y + dy) in reserved
                for dx, dy, wall_bit in DIRECTIONS.values()
            )
            if not touches_sign:
                real += 1
    return real
