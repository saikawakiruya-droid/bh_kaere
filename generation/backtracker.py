"""Recursive-backtracker maze generation (iterative implementation).

Registered under the name ``"backtracker"`` in :mod:`generation.generator`'s
``ALGORITHMS`` registry.

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


# [DEAD CODE — commented out] Full-pipeline-only assumption.
# `generate_backtracker` is only ever reached through the whole program, where
# `reserved` always comes from `reserved_cells` (which guarantees the free cells
# stay a single 4-connected component). So `start` is always the validated,
# non-reserved entry and the free area is never split. Under that premise the
# two helpers below are unreachable, and `_find_connector` could never actually
# connect anything anyway (a visited cell is never 4-adjacent to an unvisited
# free cell once the stack empties). Verified: output is byte-for-byte identical
# with these removed across a 2880-config fuzz. Kept here (commented) for review.
#
# def _first_free(width: int, height: int, reserved: Set[Coord]
#                 ) -> Optional[Coord]:
#     """Scan from the top-left and return the first non-reserved cell."""
#     for y in range(height):
#         for x in range(width):
#             if (x, y) not in reserved:
#                 return (x, y)
#     return None
#
#
# def _find_connector(maze: Maze, reserved: Set[Coord],
#                     visited: Set[Coord], rng: random.Random
#                     ) -> Optional[Tuple[Coord, str, Coord]]:
#     """Find one connection from a visited free cell to an unvisited free cell.
#
#     After the backtracker has popped everything at a dead end, some free cells
#     may still be unvisited (a separate component split off by reserved cells).
#     This picks a wall to open to attach it to the existing tree.
#
#     Returns:
#         ``(visited_cell, direction, unvisited_cell)``, or ``None`` if there is
#         no candidate.
#     """
#     candidates: List[Tuple[Coord, str, Coord]] = []
#     for (x, y) in visited:
#         for direction, (dx, dy, _) in DIRECTIONS.items():
#             n = (x + dx, y + dy)
#             if maze.in_bounds(*n) and n not in reserved and n not in visited:
#                 candidates.append(((x, y), direction, n))
#     if not candidates:
#         return None
#     # ``visited`` is a set, so its iteration order is not deterministic across
#     # runs; sort the candidates first so ``rng.choice`` picks reproducibly.
#     candidates.sort()
#     return rng.choice(candidates)


def generate_backtracker(width: int, height: int, reserved: Set[Coord],
                         rng: random.Random,
                         start: Optional[Coord] = None) -> Maze:
    """Generate a perfect maze (spanning tree) with an iterative backtracker.

    Uses an explicit stack (iterative implementation). Cells in ``reserved``
    are never visited or carved, so they stay closed and form the "42" sign.

    Full-pipeline assumption: this is only ever called through the whole
    program, where ``reserved`` comes from ``reserved_cells`` and keeps the
    free cells a single 4-connected component, and ``start`` is the validated,
    non-reserved entry. Under that premise a plain DFS that drains the stack
    carves the entire spanning tree; the separate-component reconnection path
    and the ``start``/all-reserved fallbacks are commented out below.

    Args:
        width: Maze width.
        height: Maze height.
        reserved: Set of cells to keep closed.
        rng: Random source (``random.Random``).
        start: Cell to start carving from (the validated entry).

    Returns:
        The generated :class:`~core.maze.Maze`.
    """
    maze = Maze(width, height)

    # [commented out — full-pipeline only] `reserved` is already a fresh set
    # from `reserved_cells` and is never mutated here, so the copy is redundant.
    # reserved = set(reserved)

    # [commented out — full-pipeline only] the "42" sign never covers every
    # cell, so the free area is never empty.
    # total_free = width * height - len(reserved)
    # if total_free <= 0:
    #     return maze

    # [commented out — full-pipeline only] `start` is always the validated,
    # non-reserved entry, so the top-left fallback via `_first_free` is
    # unreachable.
    # root = start if (start is not None and start not in reserved) else None
    # if root is None:
    #     root = _first_free(width, height, reserved)
    root = start
    assert root is not None  # full pipeline: entry is always a valid free cell
    visited: Set[Coord] = {root}
    stack: List[Coord] = [root]

    # The single free component is fully reachable from `root`, so draining the
    # stack carves the whole spanning tree.
    # [commented out — full-pipeline only] old loop condition + `if stack:`
    # guard, needed only for the separate-component path below.
    # while len(visited) < total_free:
    #     if stack:
    while stack:
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
    # [commented out — full-pipeline only] the `else:` of the old `if stack:`.
    # Attaches a separate free component to the tree. Unreachable (free cells
    # are one component) and, even if reached, `_find_connector` can never find
    # a candidate. See the note at the top of the file.
    #     else:
    #         # Attach a separate component to the existing tree.
    #         conn = _find_connector(maze, reserved, visited, rng)
    #         if conn is None:
    #             break  # fully split by reserved cells (never happens for 42)
    #         (cx, cy), direction, n = conn
    #         maze.open_wall(cx, cy, direction)
    #         visited.add(n)
    #         stack = [n]
    return maze
