"""mazegen — a reusable, single-file maze generation module.

A self-contained maze generator that future projects can ``pip install`` and
use. It does not depend on the other files of the main project (A-Maze-ing).

A cell encodes its walls in 4 bits (a closed wall's bit is 1)::

    bit0 = North (N), bit1 = East (E), bit2 = South (S), bit3 = West (W)

Basic usage::

    from mazegen import MazeGenerator

    # Generate a 12x8 perfect maze with a fixed seed
    gen = MazeGenerator(12, 8, seed=42)
    gen.generate()

    # Access the generated structure (2D array of wall codes)
    grid = gen.grid
    code = gen.wall_code(0, 0)

    # Get at least one solution (shortest path entry->exit)
    path = gen.solution((0, 0), (11, 7))        # e.g. "EESSE..."
    cells = gen.solution_cells((0, 0), (11, 7))  # cells on the path

    # Make an imperfect maze (with loops)
    gen2 = MazeGenerator(20, 15, seed=1, perfect=False).generate()
"""

from __future__ import annotations

import random
from collections import deque
from typing import Dict, List, Optional, Set, Tuple

__version__ = "1.0.0"
__all__ = ["MazeGenerator"]

Coord = Tuple[int, int]

WALL_N = 1 << 0
WALL_E = 1 << 1
WALL_S = 1 << 2
WALL_W = 1 << 3

# Direction -> (dx, dy, wall bit)
_DIRS: Dict[str, Tuple[int, int, int]] = {
    "N": (0, -1, WALL_N),
    "E": (1, 0, WALL_E),
    "S": (0, 1, WALL_S),
    "W": (-1, 0, WALL_W),
}
_OPP = {"N": "S", "S": "N", "E": "W", "W": "E"}


class MazeGenerator:
    """Generates a maze and provides access to its structure and solution.

    Attributes:
        width: Width (in cells).
        height: Height (in cells).
        seed: Random seed. ``None`` means random each run.
        perfect: ``True`` for a perfect maze (spanning tree), ``False`` for
            one with loops.
        grid: ``grid[y][x]`` holds each cell's 4-bit wall code (valid after
            generation).
    """

    def __init__(self, width: int, height: int, seed: Optional[int] = None,
                 perfect: bool = True,
                 rng: Optional[random.Random] = None) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("width and height must be positive integers")
        self.width = width
        self.height = height
        self.seed = seed
        self.perfect = perfect
        # An external random source can be injected (so a host program can
        # share one reproducible stream across generation and its own
        # post-processing); otherwise one is derived from ``seed``.
        self._external_rng = rng is not None
        self._rng = rng if rng is not None else random.Random(seed)
        # By default every cell is walled on all four sides.
        self.grid: List[List[int]] = [
            [0xF for _ in range(width)] for _ in range(height)
        ]

    # --- Internal helpers -------------------------------------------------
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

    def _openings(self, x: int, y: int) -> int:
        return sum(1 for d in _DIRS if self._is_open(x, y, d))

    def _first_free(self, reserved: "frozenset[Coord]") -> Coord:
        """Return the first non-reserved cell, scanning from the top-left."""
        for y in range(self.height):
            for x in range(self.width):
                if (x, y) not in reserved:
                    return (x, y)
        raise ValueError("every cell is reserved: nothing to carve")

    # --- Generation -------------------------------------------------------
    def _braid(self, ratio: float = 1.0,
               reserved: "frozenset[Coord]" = frozenset()) -> None:
        """Reduce dead ends to create loops (imperfect-maze conversion).

        Note:
            Standalone/minimal: no 3x3-open guard and no "42" protection.
        """
        dead = [(x, y) for y in range(self.height) for x in range(self.width)
                if (x, y) not in reserved and self._openings(x, y) == 1]
        self._rng.shuffle(dead)
        for (x, y) in dead[:int(len(dead) * ratio)]:
            if self._openings(x, y) != 1:
                continue
            cands = [d for d, (dx, dy, bit) in _DIRS.items()
                     if self._in_bounds(x + dx, y + dy)
                     and (x + dx, y + dy) not in reserved
                     and self.grid[y][x] & bit]
            if cands:
                self._open(x, y, self._rng.choice(cands))

    def generate(self, start: Optional[Coord] = None,
                 reserved: Optional[Set[Coord]] = None) -> "MazeGenerator":
        """Generate the maze with an iterative recursive backtracker.

        When ``perfect=False``, dead ends are reduced after generation to
        create loops.

        Args:
            start: Cell to start carving from. ``None`` (or a reserved cell)
                means the first non-reserved cell.
            reserved: Cells to keep fully closed (never visited or carved).
                The remaining free cells must stay connected; any component not
                reachable from ``start`` is left closed.

        Returns:
            Self (for method chaining).
        """
        frozen: "frozenset[Coord]" = frozenset(reserved) if reserved else frozenset()
        # Reset the random source so results are identical each run, unless an
        # external stream was injected (the host owns its lifecycle then).
        if not self._external_rng:
            self._rng = random.Random(self.seed)
        self.grid = [[0xF for _ in range(self.width)]
                     for _ in range(self.height)]

        if self.width * self.height - len(frozen) <= 0:
            return self
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

        if not self.perfect:
            self._braid(reserved=frozen)
        return self

    # --- Structure access -------------------------------------------------
    def wall_code(self, x: int, y: int) -> int:
        """Return the 4-bit wall code of cell ``(x, y)``."""
        if not self._in_bounds(x, y):
            raise ValueError(f"out of bounds: ({x},{y})")
        return self.grid[y][x]

    # --- Solution ---------------------------------------------------------
    def _distances(self, source: Coord) -> Dict[Coord, int]:
        dist: Dict[Coord, int] = {source: 0}
        q: deque[Coord] = deque([source])
        while q:
            x, y = q.popleft()
            for d, (dx, dy, _) in _DIRS.items():
                if not self._is_open(x, y, d):
                    continue
                n = (x + dx, y + dy)
                if n not in dist:
                    dist[n] = dist[(x, y)] + 1
                    q.append(n)
        return dist

    def solution(self, entry: Coord, exit_: Coord) -> Optional[str]:
        """Return the shortest path from entry to exit as ``N``/``E``/``S``/``W``.

        ``None`` if unreachable, empty string if entry == exit.
        """
        if not self._in_bounds(*entry) or not self._in_bounds(*exit_):
            raise ValueError("entry/exit is out of bounds")
        if entry == exit_:
            return ""
        d_exit = self._distances(exit_)
        if entry not in d_exit:
            return None
        steps: List[str] = []
        x, y = entry
        while (x, y) != exit_:
            remaining = d_exit[(x, y)]
            for d, (dx, dy, _) in _DIRS.items():
                if self._is_open(x, y, d) and \
                        d_exit.get((x + dx, y + dy)) == remaining - 1:
                    steps.append(d)
                    x, y = x + dx, y + dy
                    break
        return "".join(steps)

    def solution_cells(self, entry: Coord, exit_: Coord) -> Set[Coord]:
        """Return the set of cells on a shortest path (empty if unreachable)."""
        d_entry = self._distances(entry)
        d_exit = self._distances(exit_)
        if exit_ not in d_entry:
            return set()
        best = d_entry[exit_]
        return {c for c, de in d_entry.items()
                if c in d_exit and de + d_exit[c] == best}
