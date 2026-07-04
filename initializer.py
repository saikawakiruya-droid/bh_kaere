"""Module that takes config values and assembles the initial pre-generation map.

It has two roles:

1. Prepare an initial :class:`~maze.Maze` with every cell closed on all four
   sides.
2. Reserve the spec IV.4 "42" sign as **cells kept closed**. The generation
   algorithm never carves these reserved cells, so the "42" block emerges
   inside the surrounding passages.

"42" is defined as a bitmap font and placed at the center of the maze. If it
overlaps the entry/exit or the maze is too small, a distinct error is raised by
cause (all non-fatal: the maze can still be built by omitting the sign).
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Set, Tuple

from errors import SignOverlapError, SignTooBigError
from maze import Maze

Coord = Tuple[int, int]

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
                   gap: Optional[int] = None) -> Set[Coord]:
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

    Returns:
        The set of cells ``(x, y)`` to keep closed.

    Raises:
        SignTooBigError: If the sign does not fit the maze frame (width/height).
        SignOverlapError: If it fits the frame but no placement avoids
            overlapping the entry/exit or disconnecting the maze.
    """
    sign_h = GLYPH_HEIGHT
    avoid_set = set(avoid) if avoid is not None else set()

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
            if _free_connected(width, height, cells):
                return cells

    if not fits_frame:
        raise SignTooBigError(
            f"sign '{text}' does not fit the maze frame {width}x{height}"
        )
    raise SignOverlapError(
        f"no position can place sign '{text}' "
        f"(it would overlap the entry/exit or disconnect the maze)"
    )


def initialize_maze(width: int, height: int,
                    entry: Optional[Coord] = None,
                    exit_: Optional[Coord] = None,
                    sign: str = "42",
                    gap: Optional[int] = None
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

    Returns:
        A ``(maze, reserved)`` tuple. ``maze`` is the all-closed maze, and
        ``reserved`` is the set of cell coordinates to keep closed.
    """
    maze = Maze(width, height)
    avoid = {c for c in (entry, exit_) if c is not None}
    try:
        reserved = reserved_cells(width, height, sign, avoid, gap)
    except SignTooBigError as err:
        # The sign does not fit the maze frame.
        print(f"warning (does not fit): {err} / omitting sign '{sign}'")
        reserved = set()
    except SignOverlapError as err:
        # It fits the frame, but no generatable placement (overlap/disconnect).
        print(f"warning (cannot place): {err} / omitting sign '{sign}'")
        reserved = set()
    return maze, reserved
