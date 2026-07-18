"""mazegen — a reusable, single-file maze generation module.

A self-contained maze generator that future projects can ``pip install`` and
use. It does not depend on any other file of the main project (A-Maze-ing).

A cell encodes its walls in 4 bits (a closed wall's bit is 1)::

    bit0 = North (N), bit1 = East (E), bit2 = South (S), bit3 = West (W)

The whole pipeline lives here: carving a maze, embedding the "42" sign as a
reserved (fully closed) mask, and — for a playable Pac-Man board — braiding the
dead ends away while keeping passages at most 2 cells wide.

Basic usage::

    from mazegen import generate_mazes

    # Read a list of specs (dicts) and generate each; get one wall grid per spec
    grids = generate_mazes([
        {"width": 25, "height": 20, "seed": 42, "perfect": True,
         "entry": (0, 0), "exit": (24, 19)},
        {"width": 25, "height": 20, "seed": 1, "perfect": False},
    ])
    grid = grids[0]          # grid[y][x] = 4-bit wall code
    code = grid[0][0]

Spec keys: ``width`` and ``height`` are required; ``perfect`` (default True),
``seed``, ``rng`` (an injected ``random.Random`` overriding ``seed``),
``entry``, ``exit``, ``sign`` (default ``"42"``; ``""``/``None`` disables it),
``reserved`` (extra cells to keep fully closed), ``min_loops`` (default 2, used
when ``perfect`` is False) and ``gap`` (digit spacing of the sign) are optional.
"""

from __future__ import annotations

import random
import sys
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Set, Tuple

__version__ = "2.0.0"
__all__ = ["generate_mazes", "supported_sign_chars"]

Coord = Tuple[int, int]

WALL_N = 1 << 0
WALL_E = 1 << 1
WALL_S = 1 << 2
WALL_W = 1 << 3
# A cell closed on all four sides (0xF): the initial state of every cell and
# the value of the reserved "42" sign cells that stay walled in.
ALL_WALLS = WALL_N | WALL_E | WALL_S | WALL_W

# Direction -> (dx, dy, wall bit). N is y-1, S is y+1, E is x+1, W is x-1.
_DIRS: Dict[str, Tuple[int, int, int]] = {
    "N": (0, -1, WALL_N),
    "E": (1, 0, WALL_E),
    "S": (0, 1, WALL_S),
    "W": (-1, 0, WALL_W),
}
_OPP: Dict[str, str] = {"N": "S", "S": "N", "E": "W", "W": "E"}


# --------------------------------------------------------------------------- #
# Errors
# --------------------------------------------------------------------------- #
class SignError(Exception):
    """Raised when the "42" sign cannot be placed in the maze."""


class SignTooBigError(SignError):
    """Raised when the sign does not fit the maze frame at all."""


class SignOverlapError(SignError):
    """Raised when the sign fits the frame but no placement is valid."""


# --------------------------------------------------------------------------- #
# "42" sign (reserved-cell mask) generation
# --------------------------------------------------------------------------- #
# Each digit is a 3x5 bitmap. '1' = a cell kept closed. The shapes match the
# "42" figure in the assignment PDF (A-Maze-ing).
GLYPHS: Dict[str, List[str]] = {
    "4": ["100", "100", "111", "001", "001"],
    "2": ["111", "001", "111", "100", "111"],
}

GLYPH_HEIGHT = 5
GLYPH_WIDTH = 3
DEFAULT_GAP = 1
MIN_GAP = 0
MAX_GAP = 2
# Digit gaps tried by auto-selection, in priority order: 1 first, then 2.
AUTO_GAPS = (1, 2)


def supported_sign_chars() -> FrozenSet[str]:
    """Return the characters the sign can draw (the defined glyphs)."""
    return frozenset(GLYPHS)


def sign_bitmap(text: str = "42", gap: int = DEFAULT_GAP) -> List[str]:
    """Return the bitmap rows for ``text`` with ``gap`` blank columns between digits.

    Not supported: characters absent from ``GLYPHS`` (KeyError), or ``gap``
    outside ``MIN_GAP``-``MAX_GAP`` (ValueError).
    """
    if not (MIN_GAP <= gap <= MAX_GAP):
        raise ValueError(f"gap must be between {MIN_GAP} and {MAX_GAP}: {gap}")
    rows: List[str] = []
    for r in range(GLYPH_HEIGHT):
        parts = [GLYPHS[ch][r] for ch in text]
        rows.append(("0" * gap).join(parts))
    return rows


def _sign_width(num_digits: int, gap: int) -> int:
    """Return the sign width (in cells) for the digit count and gap."""
    return num_digits * GLYPH_WIDTH + (num_digits - 1) * gap


def _placements(width: int, height: int, sign_w: int, sign_h: int
                ) -> List[Coord]:
    """Return every top-left offset where the sign fits, closest-to-center first."""
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

    A cell can only be opened toward a free (non-reserved) in-bounds neighbor,
    so it needs at least two such neighbors to reach two openings.
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
    """Return whether the non-reserved (free) cells form one 4-connected group."""
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
                   corridors: Optional[Iterable[Coord]] = None,
                   also_reserved: Optional[Iterable[Coord]] = None) -> Set[Coord]:
    """Return the sign's reserved cells at the center-most generatable placement.

    Placements are tried from the center outward, keeping the first that avoids
    the ``avoid`` cells (entry/exit), keeps the free cells connected, and leaves
    every ``corridors`` cell openable. ``also_reserved`` is an extra mask that
    the sign must not overlap and that is treated as closed for the connectivity
    and corridor checks. The gap is 1 by default and only widened to 2 when no
    placement fits at 1.

    Not supported: a sign that never fits the frame (SignTooBigError), a sign
    that fits but has no valid placement (SignOverlapError), or a ``gap`` out of
    range (ValueError).
    """
    sign_h = GLYPH_HEIGHT
    avoid_set = set(avoid) if avoid is not None else set()
    mask = set(also_reserved) if also_reserved is not None else set()
    corridor_set = set(corridors) if corridors is not None else set()

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
            continue
        fits_frame = True
        bitmap = sign_bitmap(text, g)
        shape = [(rx, ry)
                 for ry, row in enumerate(bitmap)
                 for rx, ch in enumerate(row) if ch == "1"]
        for off_x, off_y in _placements(width, height, sign_w, sign_h):
            cells = {(off_x + rx, off_y + ry) for rx, ry in shape}
            if cells & (avoid_set | mask):
                continue
            if corridor_set and not _corridors_openable(
                    width, height, cells | mask, corridor_set):
                continue
            if _free_connected(width, height, cells | mask):
                return cells

    if not fits_frame:
        raise SignTooBigError(
            f"sign '{text}' does not fit the maze frame {width}x{height}"
        )
    raise SignOverlapError(
        f"no position can place sign '{text}' (it would overlap the "
        f"entry/exit, disconnect the maze, or strangle a corridor cell)"
    )


def _playable_corridors(width: int, height: int) -> Set[Coord]:
    """Return the four corners and the centre (the Pac-Man corridors)."""
    return {
        (0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1),
        (width // 2, height // 2),
    }


# --------------------------------------------------------------------------- #
# Generation engine (internal)
# --------------------------------------------------------------------------- #
class _MazeEngine:
    """Carves and braids one maze on a ``grid[y][x]`` of 4-bit wall codes."""

    def __init__(self, width: int, height: int,
                 rng: random.Random) -> None:
        self.width = width
        self.height = height
        self._rng = rng
        self.grid: List[List[int]] = [
            [ALL_WALLS for _ in range(width)] for _ in range(height)
        ]

    def _in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def _is_open(self, x: int, y: int, direction: str) -> bool:
        _, _, bit = _DIRS[direction]
        if self.grid[y][x] & bit:
            return False
        dx, dy, _ = _DIRS[direction]
        return self._in_bounds(x + dx, y + dy)

    def _open(self, x: int, y: int, direction: str) -> None:
        dx, dy, bit = _DIRS[direction]
        nx, ny = x + dx, y + dy
        _, _, obit = _DIRS[_OPP[direction]]
        self.grid[y][x] &= ~bit
        self.grid[ny][nx] &= ~obit

    def _close(self, x: int, y: int, direction: str) -> None:
        dx, dy, bit = _DIRS[direction]
        nx, ny = x + dx, y + dy
        _, _, obit = _DIRS[_OPP[direction]]
        self.grid[y][x] |= bit
        self.grid[ny][nx] |= obit

    def _openings(self, x: int, y: int) -> int:
        return sum(1 for d in _DIRS if self._is_open(x, y, d))

    def _is_open_area(self, x0: int, y0: int, w: int, h: int) -> bool:
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                if x + 1 < x0 + w and not self._is_open(x, y, "E"):
                    return False
                if y + 1 < y0 + h and not self._is_open(x, y, "S"):
                    return False
        return True

    def _first_free(self, reserved: FrozenSet[Coord]) -> Coord:
        """Return the first non-reserved cell, scanning from the top-left."""
        for y in range(self.height):
            for x in range(self.width):
                if (x, y) not in reserved:
                    return (x, y)
        raise ValueError("every cell is reserved: nothing to carve")

    def _count_loops(self, reserved: Set[Coord]) -> int:
        """Return the number of independent loops among the free cells."""
        vertices = edges = 0
        for y in range(self.height):
            for x in range(self.width):
                if (x, y) in reserved:
                    continue
                vertices += 1
                for d in ("E", "S"):
                    dx, dy, _ = _DIRS[d]
                    if (x + dx, y + dy) in reserved:
                        continue
                    if self._is_open(x, y, d):
                        edges += 1
        if vertices == 0:
            return 0
        return edges - vertices + 1

    def _creates_open_3x3(self, x: int, y: int) -> bool:
        """Return whether any 3x3 block containing ``(x, y)`` is fully open."""
        for tlx in range(max(0, x - 2), min(x, self.width - 3) + 1):
            for tly in range(max(0, y - 2), min(y, self.height - 3) + 1):
                if self._is_open_area(tlx, tly, 3, 3):
                    return True
        return False

    def _open_one_safe(self, x: int, y: int, reserved: Set[Coord]) -> bool:
        """Open one closed wall of ``(x, y)`` toward a free neighbor, safely.

        The opening is kept only if it does not create a fully open 3x3 area;
        reserved cells are never connected to.
        """
        candidates: List[str] = []
        for d, (dx, dy, bit) in _DIRS.items():
            nx, ny = x + dx, y + dy
            if (self._in_bounds(nx, ny) and (nx, ny) not in reserved
                    and self.grid[y][x] & bit):
                candidates.append(d)
        self._rng.shuffle(candidates)
        for d in candidates:
            dx, dy, _ = _DIRS[d]
            self._open(x, y, d)
            if self._creates_open_3x3(x, y) or \
                    self._creates_open_3x3(x + dx, y + dy):
                self._close(x, y, d)
            else:
                return True
        return False

    def _ensure_loops(self, reserved: Set[Coord], min_loops: int) -> None:
        """Open extra safe walls until there are at least ``min_loops`` loops.

        Stops early if no wall can be opened without creating a 3x3 open area.
        """
        free: List[Coord] = [
            (x, y)
            for y in range(self.height)
            for x in range(self.width)
            if (x, y) not in reserved
        ]
        while self._count_loops(reserved) < min_loops:
            self._rng.shuffle(free)
            progressed = False
            for (x, y) in free:
                if self._open_one_safe(x, y, reserved):
                    progressed = True
                    if self._count_loops(reserved) >= min_loops:
                        break
            if not progressed:
                break

    def carve(self, reserved: Set[Coord],
              start: Optional[Coord] = None) -> None:
        """Carve a perfect maze (spanning tree) with an iterative backtracker.

        Cells in ``reserved`` are never visited or carved. Any free component
        not reachable from ``start`` is left closed.
        """
        frozen: FrozenSet[Coord] = frozenset(reserved)
        if self.width * self.height - len(frozen) <= 0:
            return
        sx, sy = (start if (start is not None and start not in frozen)
                  else self._first_free(frozen))
        visited: Set[Coord] = {(sx, sy)}
        stack: List[Coord] = [(sx, sy)]
        while stack:
            x, y = stack[-1]
            nbrs = []
            for d, (dx, dy, _) in _DIRS.items():
                n = (x + dx, y + dy)
                if self._in_bounds(*n) and n not in frozen and n not in visited:
                    nbrs.append((d, n))
            if nbrs:
                d, n = self._rng.choice(nbrs)
                self._open(x, y, d)
                visited.add(n)
                stack.append(n)
            else:
                stack.pop()

    def braid(self, reserved: Set[Coord],
              corridors: Optional[Iterable[Coord]],
              min_loops: int, ratio: float = 1.0) -> None:
        """Turn the carved maze into a playable, loopy board in place.

        Three phases: reduce dead ends, force every ``corridors`` cell to at
        least two openings, then open extra walls until there are at least
        ``min_loops`` loops. Openings that would create a fully open 3x3 area
        are never kept, and reserved cells are never connected to.
        """
        # Phase 1: reduce dead ends.
        dead_ends: List[Coord] = [
            (x, y)
            for y in range(self.height)
            for x in range(self.width)
            if (x, y) not in reserved and self._openings(x, y) == 1
        ]
        self._rng.shuffle(dead_ends)
        for (x, y) in dead_ends[:int(len(dead_ends) * ratio)]:
            if self._openings(x, y) != 1:
                continue
            self._open_one_safe(x, y, reserved)

        # Phase 2: make the required cells open corridors (>= 2 openings).
        if corridors is not None:
            for (x, y) in corridors:
                if (x, y) in reserved or not self._in_bounds(x, y):
                    continue
                while self._openings(x, y) < 2:
                    if not self._open_one_safe(x, y, reserved):
                        break
                if self._openings(x, y) < 2:
                    print(
                        "warning: could not open corridor at "
                        f"({x},{y}) to 2 openings",
                        file=sys.stderr,
                    )

        # Phase 3: guarantee at least ``min_loops`` independent loops.
        if min_loops > 0:
            self._ensure_loops(reserved, min_loops)


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #
def _generate_one(spec: Dict[str, Any]) -> List[List[int]]:
    """Generate one maze from a spec dict and return its wall grid.

    Not supported: a missing or non-positive ``width``/``height`` (ValueError).
    A sign that cannot be placed is non-fatal: it is omitted with a warning.
    """
    width = spec["width"]
    height = spec["height"]
    if (not isinstance(width, int) or not isinstance(height, int)
            or width <= 0 or height <= 0):
        raise ValueError("width and height must be positive integers")

    perfect: bool = spec.get("perfect", True)
    rng: random.Random = spec.get("rng") or random.Random(spec.get("seed"))
    entry: Optional[Coord] = spec.get("entry")
    exit_: Optional[Coord] = spec.get("exit")
    sign: Optional[str] = spec.get("sign", "42")
    gap: Optional[int] = spec.get("gap")
    min_loops: int = spec.get("min_loops", 2)
    extra_reserved: Set[Coord] = set(spec.get("reserved") or ())

    corridors = None if perfect else _playable_corridors(width, height)

    reserved: Set[Coord] = set(extra_reserved)
    if sign:
        avoid: Set[Coord] = set()
        if entry is not None:
            avoid.add(entry)
        if exit_ is not None:
            avoid.add(exit_)
        try:
            reserved |= reserved_cells(width, height, text=sign, avoid=avoid,
                                       gap=gap, corridors=corridors,
                                       also_reserved=extra_reserved)
        except SignError as err:
            print(f"warning: sign omitted: {err}", file=sys.stderr)

    engine = _MazeEngine(width, height, rng)
    engine.carve(reserved, start=entry)
    if not perfect:
        engine.braid(reserved, corridors, min_loops)
    return engine.grid


def generate_mazes(specs: Iterable[Dict[str, Any]]) -> List[List[List[int]]]:
    """Read a list of maze specs and generate each; return one wall grid per spec.

    Each grid is ``grid[y][x]`` = a 4-bit wall code (bit0=N, 1=E, 2=S, 3=W; a
    set bit is a closed wall). The result is aligned one-to-one with ``specs``.
    See the module docstring for the spec keys.

    Not supported: a spec missing ``width``/``height`` or with non-positive
    values (ValueError).
    """
    return [_generate_one(spec) for spec in specs]
