"""Structural metrics of a maze: independent loops and dead ends.

Both metrics are read-only queries over an already-built :class:`~core.maze.Maze`
and are used from two different places for two different reasons:
:mod:`braiding.braiding` calls :func:`count_loops` while braiding to know when
to stop opening walls, and :mod:`verification.verifier` calls both to confirm
the spec IV.4 v2.2 playable-board rules (at least two loops, dead ends rare).
Kept in :mod:`core` (alongside :class:`~core.maze.Maze`) rather than under
either consumer, since it is a general-purpose Maze query, not specific to
either braiding or verification.

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
    """Return the number of *real* dead ends among the free (non-reserved) cells.

    A cell is a dead end when it has exactly one opening. For this check the
    outer border counts as a wall, but a reserved ("42") cell does *not*: a wall
    facing a sign cell is not treated as a wall here. As a result, no cell is
    reported as a dead end merely because the sign blocks its other sides -- so
    dead ends arising from the sign's presence (including around the "42"
    pattern) disappear, matching ``maze_analyzer.py``, which tolerates dead
    ends enclosed by the mandatory "42".

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
