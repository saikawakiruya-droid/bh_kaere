"""Core maze data representation and search algorithms.

A cell encodes its walls in 4 bits (a set bit means the wall is closed)::

    bit 0 (LSB) : North
    bit 1       : East
    bit 2       : South
    bit 3       : West

Coordinates are ``(x, y)``, where ``x`` is the column (width axis) and ``y``
is the row (height axis). The origin ``(0, 0)`` is the top-left corner, and
moving south increases ``y``.

This module is the single source of truth for the wall definitions reused by
both the generator and the renderer, and it also provides the search
(solving) algorithms.
"""

from __future__ import annotations

from collections import deque
from typing import Dict, List, Optional, Set, Tuple

# --- Wall bits -----------------------------------------------------------
WALL_N = 1 << 0
WALL_E = 1 << 1
WALL_S = 1 << 2
WALL_W = 1 << 3

Coord = Tuple[int, int]

# Direction label -> (dx, dy, wall bit for that direction).
#   N is y-1, S is y+1, E is x+1, W is x-1.
DIRECTIONS: Dict[str, Tuple[int, int, int]] = {
    "N": (0, -1, WALL_N),
    "E": (1, 0, WALL_E),
    "S": (0, 1, WALL_S),
    "W": (-1, 0, WALL_W),
}

# Opposite of each direction. Used to open the matching wall on both cells.
OPPOSITE: Dict[str, str] = {"N": "S", "S": "N", "E": "W", "W": "E"}


class Maze:
    """Lightweight container holding the maze as a grid of wall codes.

    Attributes:
        width: Number of cells horizontally.
        height: Number of cells vertically.
        cells: ``cells[y][x]`` holds the 4-bit wall code of each cell.
    """

    def __init__(self, width: int, height: int,
                 cells: Optional[List[List[int]]] = None) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("width and height must be positive integers")
        self.width = width
        self.height = height
        if cells is None:
            # By default every cell is closed on all four sides.
            self.cells = [[0xF for _ in range(width)] for _ in range(height)]
        else:
            if len(cells) != height or any(len(row) != width for row in cells):
                raise ValueError("cells size does not match width/height")
            self.cells = cells

    def in_bounds(self, x: int, y: int) -> bool:
        """Return whether the coordinate is inside the maze."""
        return 0 <= x < self.width and 0 <= y < self.height

    def has_wall(self, x: int, y: int, wall_bit: int) -> bool:
        """Return whether cell ``(x, y)`` has a wall in the given direction."""
        return bool(self.cells[y][x] & wall_bit)

    def is_open(self, x: int, y: int, direction: str) -> bool:
        """Return whether one can move from ``(x, y)`` toward ``direction``.

        Movement is possible only when the wall in that direction is open and
        the destination is inside the maze.
        """
        dx, dy, wall_bit = DIRECTIONS[direction]
        if self.has_wall(x, y, wall_bit):
            return False
        return self.in_bounds(x + dx, y + dy)

    def open_wall(self, x: int, y: int, direction: str) -> None:
        """Open the wall between ``(x, y)`` and its ``direction`` neighbor.

        To keep the spec IV.4 invariant "adjacent cells share the same wall",
        the matching wall bit is cleared on both sides at once.

        Args:
            x: Cell x coordinate.
            y: Cell y coordinate.
            direction: Direction to open (``N`` / ``E`` / ``S`` / ``W``).

        Raises:
            ValueError: If the destination is outside the maze.
        """
        dx, dy, bit = DIRECTIONS[direction]
        nx, ny = x + dx, y + dy
        if not self.in_bounds(nx, ny):
            raise ValueError(
                f"opening a wall out of bounds: ({x},{y}) {direction}"
            )
        _, _, opp_bit = DIRECTIONS[OPPOSITE[direction]]
        self.cells[y][x] &= ~bit
        self.cells[ny][nx] &= ~opp_bit

    def close_wall(self, x: int, y: int, direction: str) -> None:
        """Close the wall between ``(x, y)`` and its ``direction`` neighbor.

        The inverse of :meth:`open_wall`. Sets the matching wall bit on both
        sides at once.

        Args:
            x: Cell x coordinate.
            y: Cell y coordinate.
            direction: Direction to close (``N`` / ``E`` / ``S`` / ``W``).

        Raises:
            ValueError: If the destination is outside the maze.
        """
        dx, dy, bit = DIRECTIONS[direction]
        nx, ny = x + dx, y + dy
        if not self.in_bounds(nx, ny):
            raise ValueError(f"closing a wall out of bounds: ({x},{y}) {direction}")
        _, _, opp_bit = DIRECTIONS[OPPOSITE[direction]]
        self.cells[y][x] |= bit
        self.cells[ny][nx] |= opp_bit

    def is_open_area(self, x0: int, y0: int, w: int, h: int) -> bool:
        """Return whether the ``w`` x ``h`` block at ``(x0, y0)`` is fully open.

        Returns ``True`` when every internal wall between adjacent cells in the
        block is open (i.e. a single contiguous open area). Used to enforce the
        passage-width constraint (no fully open 3x3 area).
        """
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                if x + 1 < x0 + w and not self.is_open(x, y, "E"):
                    return False
                if y + 1 < y0 + h and not self.is_open(x, y, "S"):
                    return False
        return True


def bfs_distances(maze: Maze, source: Coord) -> Dict[Coord, int]:
    """Compute the shortest distance (in steps) from ``source`` to each cell.

    Runs a single breadth-first search (BFS) and computes the minimum number
    of steps from ``source`` to each cell. Because every edge has uniform
    weight, the BFS visit order is exactly the shortest distance.

    Args:
        maze: The maze to search.
        source: The cell ``(x, y)`` used as the distance origin.

    Returns:
        A ``{cell: distance}`` dict whose keys are only the reachable cells.
        ``source`` itself has distance 0. Unreachable cells are absent.

    Raises:
        ValueError: If ``source`` is outside the maze.
    """
    sx, sy = source
    if not maze.in_bounds(sx, sy):
        raise ValueError(f"source is out of bounds: {source}")

    dist: Dict[Coord, int] = {source: 0}
    queue: deque[Coord] = deque([source])
    while queue:
        x, y = queue.popleft()
        d = dist[(x, y)]
        for direction, (dx, dy, _) in DIRECTIONS.items():
            if not maze.is_open(x, y, direction):
                continue
            nxt = (x + dx, y + dy)
            if nxt in dist:
                continue
            dist[nxt] = d + 1
            queue.append(nxt)
    return dist


def solve(maze: Maze, entry: Coord, exit_: Coord) -> Optional[str]:
    """Return the shortest path from entry to exit as ``N/E/S/W`` moves.

    Builds a distance map ``d_exit`` from the exit, then repeatedly steps to
    the neighbor whose remaining distance to the exit drops by exactly 1,
    tracing a unique shortest path. Because the distances come from BFS, the
    resulting path is always shortest.

    Args:
        maze: The maze to search.
        entry: Entry coordinate ``(x, y)``.
        exit_: Exit coordinate ``(x, y)``.

    Returns:
        A path string made of ``N`` / ``E`` / ``S`` / ``W`` characters. If
        entry and exit are the same, returns an empty string; if the exit is
        unreachable, returns ``None``.

    Raises:
        ValueError: If entry or exit is outside the maze.
    """
    if not maze.in_bounds(*entry):
        raise ValueError(f"entry is out of bounds: {entry}")
    if not maze.in_bounds(*exit_):
        raise ValueError(f"exit is out of bounds: {exit_}")
    if entry == exit_:
        return ""

    # Distance map from the exit. If entry is absent, it is unreachable.
    d_exit = bfs_distances(maze, exit_)
    if entry not in d_exit:
        return None

    steps: List[str] = []
    x, y = entry
    while (x, y) != exit_:
        remaining = d_exit[(x, y)]
        for direction, (dx, dy, _) in DIRECTIONS.items():
            if not maze.is_open(x, y, direction):
                continue
            nxt = (x + dx, y + dy)
            # A neighbor 1 step closer to the exit = the next step on a
            # shortest path.
            if d_exit.get(nxt) == remaining - 1:
                steps.append(direction)
                x, y = nxt
                break
    return "".join(steps)


def solution_cells(maze: Maze, entry: Coord, exit_: Coord) -> Set[Coord]:
    """Return the set of all cells lying on a shortest path (for highlighting).

    Computes both the distance from the entry ``d_entry`` and the distance
    from the exit ``d_exit``, then collects every cell ``c`` satisfying
    ``d_entry[c] + d_exit[c] == d_entry[exit_]``. This matches exactly the set
    of cells that lie on some shortest path from entry to exit (the union of
    all shortest paths if there are several).

    Args:
        maze: The maze to search.
        entry: Entry coordinate ``(x, y)``.
        exit_: Exit coordinate ``(x, y)``.

    Returns:
        The set of cells on a shortest path. Empty if unreachable.

    Raises:
        ValueError: If entry or exit is outside the maze.
    """
    d_entry = bfs_distances(maze, entry)
    d_exit = bfs_distances(maze, exit_)
    if exit_ not in d_entry:
        return set()
    best = d_entry[exit_]
    return {
        c for c, de in d_entry.items()
        if c in d_exit and de + d_exit[c] == best
    }


def path_to_cells(entry: Coord, solution: str) -> Set[Coord]:
    """Return the cells visited by following ``solution`` from ``entry``.

    Unlike :func:`solution_cells` (which returns every cell lying on *any*
    shortest path, i.e. the union when several exist), this traces the single
    path described by the ``solution`` move string — the one shortest path the
    program reports. Renderers use it to highlight exactly **one** shortest
    path (spec V), so a board with loops never shows several overlaid paths.

    Args:
        entry: Entry coordinate ``(x, y)`` the moves start from.
        solution: A move string of ``N`` / ``E`` / ``S`` / ``W`` (e.g. from
            :func:`solve`). Characters outside those four are ignored.

    Returns:
        The set of cells on that single path (always includes ``entry``).
    """
    x, y = entry
    cells: Set[Coord] = {(x, y)}
    for step in solution:
        if step not in DIRECTIONS:
            continue
        dx, dy, _ = DIRECTIONS[step]
        x, y = x + dx, y + dy
        cells.add((x, y))
    return cells
