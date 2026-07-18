"""Recursive-backtracker maze generation (iterative implementation).

Registered under the name ``"backtracker"`` in :mod:`generation.generator`'s
``ALGORITHMS`` registry; kept in its own file so a bonus algorithm (Prim's,
Kruskal's, ...) can be added as a sibling file without touching this one.

[Spike] The carving itself is delegated to the reusable
:class:`mazegen.MazeGenerator` (the spec VI standalone module), so the project
has a single spanning-tree implementation instead of two. This thin adapter
just injects the shared RNG, forwards the reserved ("42") cells, and wraps the
resulting wall grid back into a :class:`core.maze.Maze` (both use the identical
4-bit wall layout, so the grid can be adopted directly).

Standalone usage::

    import random
    from generation.backtracker import generate_backtracker

    maze = generate_backtracker(20, 15, reserved=set(), rng=random.Random(42))
"""

from __future__ import annotations

import random
from typing import Callable, Optional, Set, Tuple

from core.maze import Maze
from mazegen import MazeGenerator

Coord = Tuple[int, int]

# Type of a generator function. Returns a maze connecting all free cells
# while avoiding reserved cells.
GeneratorFn = Callable[
    [int, int, Set[Coord], random.Random, Optional[Coord]], Maze
]


def generate_backtracker(width: int, height: int, reserved: Set[Coord],
                         rng: random.Random,
                         start: Optional[Coord] = None) -> Maze:
    """Generate a perfect maze (spanning tree) with an iterative backtracker.

    Delegates carving to :class:`mazegen.MazeGenerator` with ``perfect=True``
    (spanning tree only; playable braiding stays in :mod:`braiding.braiding`).
    The shared ``rng`` is injected so generation and the caller's later
    post-processing draw from one reproducible stream. Cells in ``reserved``
    are never visited or carved, so they stay closed and form the "42" sign.

    Args:
        width: Maze width.
        height: Maze height.
        reserved: Set of cells to keep closed.
        rng: Random source for reproducibility (``random.Random``).
        start: Cell to start carving from (the validated entry).

    Returns:
        The generated :class:`~core.maze.Maze`.
    """
    gen = MazeGenerator(width, height, perfect=True, rng=rng)
    gen.generate(start=start, reserved=reserved)
    # MazeGenerator.grid uses the same 4-bit wall layout as core.maze, so the
    # carved grid can be wrapped into a Maze without any conversion.
    return Maze(width, height, cells=gen.grid)
