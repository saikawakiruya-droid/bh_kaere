"""Recursive-backtracker maze generation (iterative implementation).

Registered under the name ``"backtracker"`` in :mod:`generation.generator`'s
``ALGORITHMS`` registry; kept in its own file so a bonus algorithm (Prim's,
Kruskal's, ...) can be added as a sibling file without touching this one.

Standalone usage::

    import random
    from generation.backtracker import generate_backtracker

    maze = generate_backtracker(20, 15, reserved=set(), rng=random.Random(42))
"""

from __future__ import annotations

import random
from typing import Callable, List, Optional, Set, Tuple

from core.maze import DIRECTIONS, Maze

Coord = Tuple[int, int]

# Type of a generator function. Returns a maze connecting all free cells
# while avoiding reserved cells.
GeneratorFn = Callable[
    [int, int, Set[Coord], random.Random, Optional[Coord]], Maze
]


def _first_free(width: int, height: int, reserved: Set[Coord]
                ) -> Optional[Coord]:
    """Scan from the top-left and return the first non-reserved cell."""
    for y in range(height):
        for x in range(width):
            if (x, y) not in reserved:
                return (x, y)
    return None


def _find_connector(maze: Maze, reserved: Set[Coord],
                    visited: Set[Coord], rng: random.Random
                    ) -> Optional[Tuple[Coord, str, Coord]]:
    """Find one connection from a visited free cell to an unvisited free cell.

    After the backtracker has popped everything at a dead end, some free cells
    may still be unvisited (a separate component split off by reserved cells).
    This picks a wall to open to attach it to the existing tree.

    Returns:
        ``(visited_cell, direction, unvisited_cell)``, or ``None`` if there is
        no candidate.
    """
    candidates: List[Tuple[Coord, str, Coord]] = []
    for (x, y) in visited:
        for direction, (dx, dy, _) in DIRECTIONS.items():
            n = (x + dx, y + dy)
            if maze.in_bounds(*n) and n not in reserved and n not in visited:
                candidates.append(((x, y), direction, n))
    if not candidates:
        return None
    return rng.choice(candidates)


def generate_backtracker(width: int, height: int, reserved: Set[Coord],
                         rng: random.Random,
                         start: Optional[Coord] = None) -> Maze:
    """Generate a perfect maze (spanning tree) with an iterative backtracker.

    Uses an explicit stack (iterative implementation), so even large mazes do
    not hit Python's recursion limit. Cells in ``reserved`` are never visited
    or carved, so they stay closed and form the "42" sign. If the free area is
    split by reserved cells, connecting walls are opened to join all free cells
    into a single tree.

    Args:
        width: Maze width.
        height: Maze height.
        reserved: Set of cells to keep closed.
        rng: Random source for reproducibility (``random.Random``).
        start: Cell to start carving from (usually the entry). If it is a
            reserved cell or ``None``, start from the top-left free cell.

    Returns:
        The generated :class:`~core.maze.Maze`.
    """
    maze = Maze(width, height)
    reserved = set(reserved)
    total_free = width * height - len(reserved)
    if total_free <= 0:
        return maze

    root = start if (start is not None and start not in reserved) else None
    if root is None:
        root = _first_free(width, height, reserved)
    assert root is not None  # total_free > 0, so one always exists
    visited: Set[Coord] = {root}
    stack: List[Coord] = [root]

    while len(visited) < total_free:
        if stack:
            x, y = stack[-1]
            unvisited = []
            for direction, (dx, dy, _) in DIRECTIONS.items():
                n = (x + dx, y + dy)
                if (maze.in_bounds(*n) and n not in reserved
                        and n not in visited):
                    unvisited.append((direction, n))
            if unvisited:
                direction, n = rng.choice(unvisited)
                maze.open_wall(x, y, direction)
                visited.add(n)
                stack.append(n)
            else:
                stack.pop()
        else:
            # Attach a separate component to the existing tree.
            conn = _find_connector(maze, reserved, visited, rng)
            if conn is None:
                break  # fully split by reserved cells (never happens for 42)
            (cx, cy), direction, n = conn
            maze.open_wall(cx, cy, direction)
            visited.add(n)
            stack = [n]
    return maze
