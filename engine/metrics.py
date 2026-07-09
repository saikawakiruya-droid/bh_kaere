"""Structural metrics of a maze: independent loops and dead ends.

Both metrics are read-only queries over an already-built :class:`~engine.maze.Maze`
and are used from two different places for two different reasons:
:mod:`engine.braiding` calls :func:`count_loops` while braiding to know when to
stop opening walls, and :mod:`engine.validator` calls both to confirm the spec
IV.4 v2.2 playable-board rules (at least two loops, dead ends rare).

Standalone usage::

    from engine.metrics import count_loops, count_dead_ends

    loops = count_loops(maze, reserved=set())
    dead_ends = count_dead_ends(maze, reserved=set())
"""

from __future__ import annotations

from typing import Set, Tuple

from engine.maze import DIRECTIONS, Maze

Coord = Tuple[int, int]


def count_loops(maze: Maze, reserved: Set[Coord]) -> int:
    """Return the number of independent loops among the free (non-reserved) cells.

    For a connected graph the cycle rank (number of independent loops) is
    ``edges - vertices + 1``. The free cells stay connected throughout braiding
    (walls are only opened, never closed), so this formula holds. A perfect
    maze (spanning tree) has ``edges = vertices - 1`` and therefore 0 loops;
    each extra opened wall adds exactly one loop.

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
    """Return the number of free cells that have exactly one opening."""
    return sum(
        1
        for y in range(maze.height)
        for x in range(maze.width)
        if (x, y) not in reserved and maze.count_openings(x, y) == 1
    )
