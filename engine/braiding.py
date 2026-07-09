"""Imperfect-maze conversion (braiding) into a playable board.

When ``PERFECT=False``, the dead ends of a perfect maze (spanning tree) are
reduced to create loops (multiple paths), and the result is shaped into a
board directly usable by a Pac-Man-like game (spec IV.4, v2.2):

- dead ends are removed so a chased player is rarely trapped;
- the four corners and the centre are kept as open corridors (they are already
  reserved-free by the initializer, and are given at least two openings here);
- at least two independent loops are guaranteed, so there is always an
  alternative route.

Every wall removal is checked so it never creates a **fully open 3x3 area**;
passages therefore stay at most 2 cells wide. Reserved cells (the "42" sign)
are never opened or connected to. Independent-loop counting lives in
:mod:`engine.metrics` (``count_loops``), used here to satisfy the loop
guarantee.

Standalone usage::

    import random
    from engine.braiding import braid

    rng = random.Random(1)
    braid(maze, reserved=set(), rng=rng, min_loops=2)  # modifies maze in place
"""

from __future__ import annotations

import random
from typing import Iterable, List, Optional, Set, Tuple

from engine.maze import DIRECTIONS, Maze
from engine.metrics import count_loops

Coord = Tuple[int, int]


def _creates_open_3x3(maze: Maze, x: int, y: int) -> bool:
    """Return whether any 3x3 block containing ``(x, y)`` is fully open."""
    for tlx in range(max(0, x - 2), min(x, maze.width - 3) + 1):
        for tly in range(max(0, y - 2), min(y, maze.height - 3) + 1):
            if maze.is_open_area(tlx, tly, 3, 3):
                return True
    return False


def _open_one_safe(maze: Maze, x: int, y: int, reserved: Set[Coord],
                   rng: random.Random) -> bool:
    """Open one currently-closed wall of ``(x, y)`` toward a free neighbor.

    A candidate wall must lead to an in-bounds, non-reserved cell and must be
    closed now. The opening is kept only if it does not create a fully open
    3x3 area (otherwise it is undone). Reserved cells ("42") are never touched.

    Returns:
        ``True`` if a wall was opened, ``False`` if none could be opened
        safely.
    """
    candidates: List[str] = []
    for d, (dx, dy, bit) in DIRECTIONS.items():
        nx, ny = x + dx, y + dy
        if (maze.in_bounds(nx, ny) and (nx, ny) not in reserved
                and maze.has_wall(x, y, bit)):
            candidates.append(d)
    rng.shuffle(candidates)

    for d in candidates:
        dx, dy, _ = DIRECTIONS[d]
        maze.open_wall(x, y, d)
        if _creates_open_3x3(maze, x, y) or \
                _creates_open_3x3(maze, x + dx, y + dy):
            maze.close_wall(x, y, d)
        else:
            return True
    return False


def _ensure_loops(maze: Maze, reserved: Set[Coord], rng: random.Random,
                  min_loops: int) -> int:
    """Open extra safe walls until there are at least ``min_loops`` loops.

    Because the free cells are already connected, any wall opened between two
    free cells adds exactly one independent loop. Stops early if no wall can be
    opened without creating a 3x3 open area.

    Returns:
        The number of walls opened.
    """
    free: List[Coord] = [
        (x, y)
        for y in range(maze.height)
        for x in range(maze.width)
        if (x, y) not in reserved
    ]
    opened = 0
    while count_loops(maze, reserved) < min_loops:
        rng.shuffle(free)
        progressed = False
        for (x, y) in free:
            if _open_one_safe(maze, x, y, reserved, rng):
                opened += 1
                progressed = True
                if count_loops(maze, reserved) >= min_loops:
                    break
        if not progressed:
            break  # cannot reach the target without a 3x3 open area
    return opened


def braid(maze: Maze, reserved: Set[Coord], rng: random.Random,
          ratio: float = 1.0,
          corridors: Optional[Iterable[Coord]] = None,
          min_loops: int = 0) -> int:
    """Turn a perfect maze into a playable, loopy board in place.

    The transformation runs in three phases:

    1. **Dead-end reduction** — for each dead end (a cell with a single
       opening), open one closed wall to connect it elsewhere.
    2. **Corridor enforcement** — every cell in ``corridors`` (the four corners
       and the centre for a Pac-Man board) is given at least two openings so it
       is a through-corridor rather than a dead end.
    3. **Loop guarantee** — extra walls are opened until there are at least
       ``min_loops`` independent loops.

    Openings that would create a fully open 3x3 area are never kept, and
    reserved cells ("42") are never connected to. Connectivity is preserved
    because walls are only opened.

    Args:
        maze: The target maze (modified in place).
        reserved: Set of reserved cells ("42") that must not be touched.
        rng: Random source.
        ratio: Fraction of dead ends to process in phase 1 (0.0-1.0).
        corridors: Cells that must end up with at least two openings. ``None``
            skips phase 2 (backward-compatible plain braiding).
        min_loops: Minimum number of independent loops to guarantee. ``0``
            skips phase 3.

    Returns:
        The number of walls actually opened.
    """
    reserved = set(reserved)
    opened = 0

    # Phase 1: reduce dead ends.
    dead_ends: List[Coord] = [
        (x, y)
        for y in range(maze.height)
        for x in range(maze.width)
        if (x, y) not in reserved and maze.count_openings(x, y) == 1
    ]
    rng.shuffle(dead_ends)
    target = int(len(dead_ends) * ratio)
    for (x, y) in dead_ends[:target]:
        # A previous operation may have changed the opening count, so recheck.
        if maze.count_openings(x, y) != 1:
            continue
        if _open_one_safe(maze, x, y, reserved, rng):
            opened += 1

    # Phase 2: make the required cells open corridors (>= 2 openings).
    if corridors is not None:
        for (x, y) in corridors:
            if (x, y) in reserved or not maze.in_bounds(x, y):
                continue
            while maze.count_openings(x, y) < 2:
                if not _open_one_safe(maze, x, y, reserved, rng):
                    break
                opened += 1

    # Phase 3: guarantee at least ``min_loops`` independent loops.
    if min_loops > 0:
        opened += _ensure_loops(maze, reserved, rng, min_loops)

    return opened
