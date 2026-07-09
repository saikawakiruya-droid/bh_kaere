"""Build a maze from scratch: sign reservation, generation, and braiding.

This module bundles the three steps that turn an empty frame into a finished
maze. Each step is independently usable — you can import just one function and
ignore the rest, exactly like copying a single file out of this package:

1. **Sign reservation** (``reserved_cells`` / ``initialize_maze``) — reserve
   the spec IV.4 "42" sign as cells the generator must never carve.
2. **Generation** (``generate_backtracker`` / ``get_algorithm``) — carve a
   perfect maze (spanning tree) with an iterative recursive backtracker.
3. **Braiding** (``braid``) — turn a perfect maze into a playable, loopy board
   (spec IV.4 v2.2: open corners/centre, at least 2 independent loops, rare
   dead ends), used only when ``PERFECT=False``.

Standalone usage (generation only, no sign, no braiding)::

    import random
    from engine.build import generate_backtracker

    maze = generate_backtracker(20, 15, reserved=set(), rng=random.Random(42))

Standalone usage (full build: sign + generation + braiding)::

    import random
    from engine.build import initialize_maze, generate_backtracker, braid

    rng = random.Random(42)
    _, reserved = initialize_maze(20, 15, entry=(0, 0), exit_=(19, 14))
    maze = generate_backtracker(20, 15, reserved, rng, start=(0, 0))
    braid(maze, reserved, rng, min_loops=2)  # skip this call for PERFECT=True
"""

from __future__ import annotations

import random
from typing import Callable, Dict, Iterable, List, Optional, Set, Tuple

from engine.errors import ConfigValueError, SignOverlapError, SignTooBigError
from engine.maze import DIRECTIONS, Maze

Coord = Tuple[int, int]

# ===========================================================================
# 1. Sign reservation and initial (all-closed) maze
# ===========================================================================
#
# Reserve the spec IV.4 "42" sign as cells kept closed. The generation
# algorithm never carves these reserved cells, so the "42" block emerges
# inside the surrounding passages. "42" is defined as a bitmap font and placed
# at the center of the maze. If it overlaps the entry/exit or the maze is too
# small, a distinct error is raised by cause (all non-fatal: the maze can
# still be built by omitting the sign).

# Each digit is defined as a 3x5 bitmap. '1' = a cell kept closed.
# The shapes match the "42" figure in the assignment PDF (A-Maze-ing).
GLYPHS: Dict[str, List[str]] = {
    "4": [
        "100",
        "100",
        "111",
        "001",
        "001",
    ],
    "2": [
        "111",
        "001",
        "111",
        "100",
        "111",
    ],
}

GLYPH_HEIGHT = 5
GLYPH_WIDTH = 3
# Default number of blank columns between digits (basically 1 cell).
DEFAULT_GAP = 1
# Minimum/maximum columns allowed between digits. 3+ columns is too far apart,
# so cap at 2.
MIN_GAP = 0
MAX_GAP = 2
# Digit gaps tried by auto-selection, in priority order: 1 first, then 2 only
# if it does not fit.
AUTO_GAPS = (1, 2)


def sign_bitmap(text: str = "42", gap: int = DEFAULT_GAP) -> List[str]:
    """Return the list of bitmap rows for ``text`` concatenated together.

    The sign is always at its natural scale (fixed size per the PDF). Only the
    ``gap`` between digits can be adjusted.

    Args:
        text: The string to draw (only digits defined in ``GLYPHS``).
        gap: Blank columns between digits (``MIN_GAP``-``MAX_GAP``).

    Returns:
        A list of row strings made of ``'1'`` / ``'0'``.

    Raises:
        KeyError: If ``text`` contains an undefined character.
        ValueError: If ``gap`` is out of range.
    """
    if not (MIN_GAP <= gap <= MAX_GAP):
        raise ValueError(
            f"gap must be between {MIN_GAP} and {MAX_GAP}: {gap}"
        )

    # Concatenate the digits horizontally on each row (gap blank columns
    # between digits).
    rows: List[str] = []
    for r in range(GLYPH_HEIGHT):
        parts = [GLYPHS[ch][r] for ch in text]
        rows.append(("0" * gap).join(parts))
    return rows


def _sign_width(num_digits: int, gap: int) -> int:
    """Return the sign width (in cells) for the given digit count and gap."""
    return num_digits * GLYPH_WIDTH + (num_digits - 1) * gap


def _placements(width: int, height: int, sign_w: int, sign_h: int
                ) -> List[Coord]:
    """Return all top-left offsets where the sign fits, closest-to-center first."""
    cx = (width - sign_w) // 2
    cy = (height - sign_h) // 2
    offs = [(ox, oy)
            for ox in range(0, width - sign_w + 1)
            for oy in range(0, height - sign_h + 1)]
    offs.sort(key=lambda o: (abs(o[0] - cx) + abs(o[1] - cy), o))
    return offs


def _corridors_openable(width: int, height: int, reserved: Set[Coord],
                        corridors: Set[Coord]) -> bool:
    """Return whether every ``corridors`` cell can still become an open corridor.

    Spec IV.4 (``PERFECT=False``) requires the four corners and the centre to be
    **open corridors**, i.e. to end up with at least two openings. A cell can
    only be opened toward a free (non-reserved) in-bounds neighbor, so it needs
    at least two such neighbors. Reserving the "42" sign right around a corridor
    cell would strangle it into a dead end that no braiding could repair.
    """
    for (x, y) in corridors:
        if (x, y) in reserved:
            return False
        free_neighbors = sum(
            1
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
            if 0 <= x + dx < width and 0 <= y + dy < height
            and (x + dx, y + dy) not in reserved
        )
        if free_neighbors < 2:
            return False
    return True


def _free_connected(width: int, height: int, reserved: Set[Coord]) -> bool:
    """Return whether the non-reserved (free) cells form one 4-connected group.

    This tests whether "the maze can still be generated after reserving the
    sign" (i.e. whether all free cells can be joined into a single tree). If it
    is not connected, generation would leave isolated cells.
    """
    free = {(x, y)
            for y in range(height) for x in range(width)
            if (x, y) not in reserved}
    if not free:
        return False
    start = next(iter(free))
    seen = {start}
    stack = [start]
    while stack:
        x, y = stack.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy)
            if n in free and n not in seen:
                seen.add(n)
                stack.append(n)
    return len(seen) == len(free)


def reserved_cells(width: int, height: int,
                   text: str = "42",
                   avoid: Optional[Iterable[Coord]] = None,
                   gap: Optional[int] = None,
                   corridors: Optional[Iterable[Coord]] = None) -> Set[Coord]:
    """Return the sign's reserved-cell coordinates at a generatable placement.

    The sign is always the same fixed size (per the PDF). The decision is based
    not on size but on **"can the maze still be generated after reserving the
    sign"** (i.e. whether the remaining free cells stay connected as one).
    Placements are tried from closest to the center, looking for a position
    that neither overlaps the entry/exit (``avoid``) nor disconnects the free
    cells, and the first one found is used.

    The digit gap is 1 cell by default (``DEFAULT_GAP``). Only when no position
    works at gap 1 is gap 2 tried (``AUTO_GAPS``). It does not widen to 2
    unnecessarily.

    Args:
        width: Maze width (in cells).
        height: Maze height (in cells).
        text: The string to draw.
        avoid: Coordinates the sign must not overlap (entry/exit, etc.).
        gap: Digit gap (``MIN_GAP``-``MAX_GAP``). ``None`` for auto-select.
        corridors: Cells that must stay openable as through-corridors (the four
            corners and the centre for a playable board, spec IV.4). A
            placement that leaves any of them with fewer than two free
            neighbors is rejected, since braiding could never lift it out of a
            dead end.

    Returns:
        The set of cells ``(x, y)`` to keep closed.

    Raises:
        SignTooBigError: If the sign does not fit the maze frame (width/height).
        SignOverlapError: If it fits the frame but no placement avoids
            overlapping the entry/exit, disconnecting the maze, or strangling a
            required corridor cell.
    """
    sign_h = GLYPH_HEIGHT
    avoid_set = set(avoid) if avoid is not None else set()
    corridor_set = set(corridors) if corridors is not None else set()

    # Gaps to try: auto -> 1 then 2; explicit -> only that value.
    if gap is None:
        gap_candidates = list(AUTO_GAPS)
    else:
        if not (MIN_GAP <= gap <= MAX_GAP):
            raise ValueError(
                f"gap must be between {MIN_GAP} and {MAX_GAP}: {gap}"
            )
        gap_candidates = [gap]

    fits_frame = False
    for g in gap_candidates:
        sign_w = _sign_width(len(text), g)
        if sign_w > width or sign_h > height:
            continue  # does not fit the frame at this gap
        fits_frame = True
        bitmap = sign_bitmap(text, g)
        shape = [(rx, ry)
                 for ry, row in enumerate(bitmap)
                 for rx, ch in enumerate(row) if ch == "1"]
        # From placements nearest the center, find one that neither overlaps
        # nor disconnects the maze.
        for off_x, off_y in _placements(width, height, sign_w, sign_h):
            cells = {(off_x + rx, off_y + ry) for rx, ry in shape}
            if cells & avoid_set:
                continue
            if corridor_set and not _corridors_openable(
                    width, height, cells, corridor_set):
                continue
            if _free_connected(width, height, cells):
                return cells

    if not fits_frame:
        raise SignTooBigError(
            f"sign '{text}' does not fit the maze frame {width}x{height}"
        )
    raise SignOverlapError(
        f"no position can place sign '{text}' (it would overlap the "
        f"entry/exit, disconnect the maze, or strangle a corridor cell)"
    )


def initialize_maze(width: int, height: int,
                    entry: Optional[Coord] = None,
                    exit_: Optional[Coord] = None,
                    sign: str = "42",
                    gap: Optional[int] = None,
                    corridors: Optional[Iterable[Coord]] = None
                    ) -> Tuple[Maze, Set[Coord]]:
    """Build an all-closed maze and reserve the "42" sign cells.

    A helper that prepares the initial state passed to the generation
    algorithm. The returned maze has every cell at ``0xF`` (walled on all four
    sides), and the reserved set is the cells to keep closed to form the sign.

    If ``entry`` / ``exit_`` are given, the sign is checked not to overlap
    them. If the sign cannot be placed, it is omitted per spec IV.4 (the
    reserved set is empty), and a cause-specific message is printed to the
    console. Both cases are non-fatal: the maze itself is built fine.

    Args:
        width: Maze width (in cells).
        height: Maze height (in cells).
        entry: Entry coordinate (avoided by the sign).
        exit_: Exit coordinate (avoided by the sign).
        sign: The string to embed.
        gap: Digit gap (``MIN_GAP``-``MAX_GAP``). ``None`` to auto-select
            based on the width.
        corridors: Cells that must become open corridors. Used by the playable
            ``PERFECT=False`` mode to keep the four corners and the centre
            free (spec IV.4). The sign neither overlaps them nor reserves so
            many of their neighbors that they could not reach two openings.

    Returns:
        A ``(maze, reserved)`` tuple. ``maze`` is the all-closed maze, and
        ``reserved`` is the set of cell coordinates to keep closed.
    """
    maze = Maze(width, height)
    avoid = {c for c in (entry, exit_) if c is not None}
    if corridors is not None:
        avoid |= set(corridors)
    try:
        reserved = reserved_cells(width, height, sign, avoid, gap, corridors)
    except SignTooBigError as err:
        # The sign does not fit the maze frame.
        print(f"warning (does not fit): {err} / omitting sign '{sign}'")
        reserved = set()
    except SignOverlapError as err:
        # It fits the frame, but no generatable placement (overlap/disconnect).
        print(f"warning (cannot place): {err} / omitting sign '{sign}'")
        reserved = set()
    return maze, reserved


# ===========================================================================
# 2. Generation algorithms and their selection registry
# ===========================================================================
#
# Currently the only choice is the **recursive backtracker**, but a mechanism
# to select it via the ``ALGORITHM`` config key is provided from the start (to
# add more algorithms as a bonus, just register them in ``ALGORITHMS``).
#
# Every generator function shares the same signature ``(width, height,
# reserved, rng, start) -> Maze``. ``reserved`` is the set of cells kept closed
# for the "42" sign, and generation never carves them.

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
        The generated :class:`~engine.maze.Maze`.
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


# --- Algorithm selection registry ----------------------------------------
ALGORITHMS: Dict[str, GeneratorFn] = {
    "backtracker": generate_backtracker,
}


def algorithm_names() -> List[str]:
    """Return the available algorithm names in ascending order."""
    return sorted(ALGORITHMS)


def get_algorithm(name: str) -> GeneratorFn:
    """Look up a generator function by name.

    Args:
        name: Algorithm name (the ``ALGORITHM`` config value).

    Returns:
        The corresponding generator function.

    Raises:
        ConfigValueError: If the algorithm name is unknown.
    """
    try:
        return ALGORITHMS[name]
    except KeyError:
        raise ConfigValueError(
            f"unknown algorithm '{name}'. choices: {algorithm_names()}"
        )


# ===========================================================================
# 3. Braiding (imperfect-maze conversion) and playable-board enforcement
# ===========================================================================
#
# When ``PERFECT=False``, the dead ends of a perfect maze (spanning tree) are
# reduced to create loops (multiple paths), and the result is shaped into a
# board directly usable by a Pac-Man-like game (spec IV.4, v2.2):
#
# - dead ends are removed so a chased player is rarely trapped;
# - the four corners and the centre are kept as open corridors (they are
#   already reserved-free by the initializer, and are given at least two
#   openings here);
# - at least two independent loops are guaranteed, so there is always an
#   alternative route.
#
# Every wall removal is checked so it never creates a **fully open 3x3 area**;
# passages therefore stay at most 2 cells wide. Reserved cells (the "42" sign)
# are never opened or connected to.


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
        if (x, y) not in reserved and _openings(maze, x, y) == 1
    )


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
        if (x, y) not in reserved and _openings(maze, x, y) == 1
    ]
    rng.shuffle(dead_ends)
    target = int(len(dead_ends) * ratio)
    for (x, y) in dead_ends[:target]:
        # A previous operation may have changed the opening count, so recheck.
        if _openings(maze, x, y) != 1:
            continue
        if _open_one_safe(maze, x, y, reserved, rng):
            opened += 1

    # Phase 2: make the required cells open corridors (>= 2 openings).
    if corridors is not None:
        for (x, y) in corridors:
            if (x, y) in reserved or not maze.in_bounds(x, y):
                continue
            while _openings(maze, x, y) < 2:
                if not _open_one_safe(maze, x, y, reserved, rng):
                    break
                opened += 1

    # Phase 3: guarantee at least ``min_loops`` independent loops.
    if min_loops > 0:
        opened += _ensure_loops(maze, reserved, rng, min_loops)

    return opened
