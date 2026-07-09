"""Dedicated module that checks whether a maze satisfies the spec IV.4 rules.

There are two ways to use it:

1. **As a library** — call :func:`validate` right after generation to get the
   list of problems (empty means valid). The main pipeline uses this to confirm
   post-generation that "a compliant maze was produced".
2. **As a command** — ``python -m engine.validator <output_file>`` reads an
   output file (spec IV.5 format) and validates its structure.

Conditions checked:

- Entry and exit are in bounds and differ from each other
- Every outward wall of the border cells is closed
- Adjacent cells share walls consistently (east-open iff neighbor's west-open)
- Every non-reserved ("42") cell is connected, with no isolated cells
- Reserved cells are closed on all four sides (the "42" is visible)
- No fully open 3x3 area (passages are at most 2 cells wide)
- When ``PERFECT``, exactly one path between entry and exit (no cycles)
- The attached shortest path is actually walkable and is shortest

Standalone usage::

    from engine.maze import Maze
    from engine.validator import validate

    maze = Maze(5, 5)
    problems = validate(maze, entry=(0, 0), exit_=(4, 4))
    if problems:
        print(f"{len(problems)} problem(s):", *problems, sep="\n  - ")
"""

from __future__ import annotations

import sys
from typing import List, Optional, Set, Tuple

from engine.maze import (
    DIRECTIONS,
    OPPOSITE,
    WALL_E,
    WALL_N,
    WALL_S,
    WALL_W,
    Maze,
    bfs_distances,
)

Coord = Tuple[int, int]


def _check_endpoints(maze: Maze, entry: Coord, exit_: Coord) -> List[str]:
    problems: List[str] = []
    if not maze.in_bounds(*entry):
        problems.append(f"entry out of bounds: {entry}")
    if not maze.in_bounds(*exit_):
        problems.append(f"exit out of bounds: {exit_}")
    if entry == exit_:
        problems.append(f"entry and exit are identical: {entry}")
    return problems


def _check_border(maze: Maze) -> List[str]:
    """Check that every outward wall of the border cells is closed."""
    problems: List[str] = []
    w, h = maze.width, maze.height
    for x in range(w):
        if not maze.has_wall(x, 0, WALL_N):
            problems.append(f"missing border wall (north): ({x},0)")
        if not maze.has_wall(x, h - 1, WALL_S):
            problems.append(f"missing border wall (south): ({x},{h - 1})")
    for y in range(h):
        if not maze.has_wall(0, y, WALL_W):
            problems.append(f"missing border wall (west): (0,{y})")
        if not maze.has_wall(w - 1, y, WALL_E):
            problems.append(f"missing border wall (east): ({w - 1},{y})")
    return problems


def _check_wall_consistency(maze: Maze) -> List[str]:
    """Check that adjacent cells hold their shared wall consistently."""
    problems: List[str] = []
    for y in range(maze.height):
        for x in range(maze.width):
            for direction, (dx, dy, _) in DIRECTIONS.items():
                nx, ny = x + dx, y + dy
                if not maze.in_bounds(nx, ny):
                    continue
                here = maze.is_open(x, y, direction)
                there = maze.is_open(nx, ny, OPPOSITE[direction])
                if here != there:
                    problems.append(
                        f"wall mismatch: ({x},{y}){direction} vs "
                        f"({nx},{ny}){OPPOSITE[direction]}"
                    )
    return problems


def _check_connectivity(maze: Maze, entry: Coord,
                        reserved: Set[Coord]) -> List[str]:
    """Check that non-reserved cells are connected and reserved cells are closed.

    The reserved cells of the "42" sign are isolated cells closed on all four
    sides (``0xF``), which is an exception allowed by the spec. Since an output
    file does not record the reserved cells, ``0xF`` cells are treated as
    reserved (allowed isolation) and excluded from the connectivity check. If
    ``reserved`` is provided, it also checks that those are actually all closed.
    """
    problems: List[str] = []
    for (x, y) in reserved:
        if maze.cells[y][x] != 0xF:
            problems.append(f"reserved cell is open: ({x},{y})")

    # Fully closed cells (the 42 sign) are excluded from connectivity as
    # allowed isolation.
    closed = {(x, y) for y in range(maze.height) for x in range(maze.width)
              if maze.cells[y][x] == 0xF}
    free = {(x, y) for y in range(maze.height) for x in range(maze.width)
            if (x, y) not in closed}
    if entry in closed:
        problems.append(f"entry sits on a fully closed cell: {entry}")
        return problems
    reachable = set(bfs_distances(maze, entry).keys())
    isolated = free - reachable
    if isolated:
        sample = sorted(isolated)[:5]
        problems.append(
            f"isolated cells present ({len(isolated)}): e.g. {sample}"
        )
    return problems


def _check_no_open_3x3(maze: Maze) -> List[str]:
    """Check that there is no fully open 3x3 area."""
    problems: List[str] = []
    for y in range(maze.height - 2):
        for x in range(maze.width - 2):
            if maze.is_open_area(x, y, 3, 3):
                problems.append(f"3x3 open area: top-left ({x},{y})")
    return problems


def _openings(maze: Maze, x: int, y: int) -> int:
    """Return the number of open walls (passages) of cell ``(x, y)``."""
    return sum(1 for d in DIRECTIONS if maze.is_open(x, y, d))


def _special_cells(maze: Maze) -> Set[Coord]:
    """Return the four corners and the centre (Pac-Man corridors, spec IV.4)."""
    w, h = maze.width, maze.height
    return {(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, h // 2)}


def _check_playable(maze: Maze, entry: Coord,
                    reserved: Set[Coord]) -> List[str]:
    """Check the spec v2.2 "playable board" rules for ``PERFECT=False``.

    A default (non-perfect) maze must be usable by a Pac-Man-like game: the
    four corners and the centre are open corridors (two or more openings each,
    so they are through-corridors rather than dead ends), there are at least
    two independent routes (loops), and dead ends stay rare.
    """
    problems: List[str] = []

    # Four corners and centre must be open (free) and reachable corridors.
    # "Open corridor" means at least two openings: a cell with a single opening
    # is a dead end, which the spec forbids for these cells.
    reachable: Set[Coord] = set()
    if maze.in_bounds(*entry):
        reachable = set(bfs_distances(maze, entry).keys())
    for (x, y) in sorted(_special_cells(maze)):
        if (x, y) in reserved or maze.cells[y][x] == 0xF:
            problems.append(
                f"corner/centre is closed, not an open corridor: ({x},{y})"
            )
        elif (x, y) not in reachable:
            problems.append(f"corner/centre is not reachable: ({x},{y})")
        elif _openings(maze, x, y) < 2:
            problems.append(
                f"corner/centre is a dead end, not an open corridor: "
                f"({x},{y}) has {_openings(maze, x, y)} opening(s)"
            )

    # At least two independent loops (a perfect maze, or one with a single
    # removed wall, is not acceptable).
    free_count = maze.width * maze.height - len(reserved)
    if free_count > 0:
        loops = _count_open_edges(maze, reserved) - free_count + 1
        if loops < 2:
            problems.append(
                f"playable board needs at least 2 independent loops, "
                f"found {loops}"
            )

    # Dead ends should be rare (a couple are tolerated; zero is the bonus).
    dead = [(x, y)
            for y in range(maze.height) for x in range(maze.width)
            if (x, y) not in reserved and _openings(maze, x, y) == 1]
    threshold = max(4, free_count // 25)
    if len(dead) > threshold:
        problems.append(
            f"too many dead ends for a playable board: {len(dead)} "
            f"(tolerated up to {threshold})"
        )
    return problems


def _count_open_edges(maze: Maze, reserved: Set[Coord]) -> int:
    """Count the number of open passages (edges) between free cells."""
    edges = 0
    for y in range(maze.height):
        for x in range(maze.width):
            if (x, y) in reserved:
                continue
            for direction in ("E", "S"):
                dx, dy, _ = DIRECTIONS[direction]
                n = (x + dx, y + dy)
                if n in reserved:
                    continue
                if maze.is_open(x, y, direction):
                    edges += 1
    return edges


def _check_perfect(maze: Maze, reserved: Set[Coord]) -> List[str]:
    """Check for a perfect maze (spanning tree): connected and edges = vertices - 1."""
    free_count = maze.width * maze.height - len(reserved)
    edges = _count_open_edges(maze, reserved)
    if free_count > 0 and edges != free_count - 1:
        return [
            f"not a perfect maze: edges {edges} != free cells - 1 "
            f"({free_count - 1}) (cycle or disconnection present)"
        ]
    return []


def _check_solution(maze: Maze, entry: Coord, exit_: Coord,
                    solution: Optional[str]) -> List[str]:
    """Check that the attached path is walkable and shortest."""
    if solution is None:
        return ["shortest path not set"]
    x, y = entry
    for step in solution:
        if step not in DIRECTIONS:
            return [f"invalid character in path: '{step}'"]
        if not maze.is_open(x, y, step):
            return [f"path passes through a wall: ({x},{y}){step}"]
        dx, dy, _ = DIRECTIONS[step]
        x, y = x + dx, y + dy
    if (x, y) != exit_:
        return [f"path does not reach the exit: end ({x},{y}) != {exit_}"]
    dist = bfs_distances(maze, entry).get(exit_)
    if dist is not None and len(solution) != dist:
        return [f"path is not shortest: length {len(solution)} != shortest {dist}"]
    return []


def validate(maze: Maze, entry: Coord, exit_: Coord,
             reserved: Optional[Set[Coord]] = None,
             perfect: bool = False,
             solution: Optional[str] = None,
             playable: bool = False) -> List[str]:
    """Validate the maze against all conditions and return the list of problems.

    Args:
        maze: The maze to validate.
        entry: Entry coordinate.
        exit_: Exit coordinate.
        reserved: Set of reserved cells ("42"); empty if omitted.
        perfect: Whether a perfect maze is required.
        solution: The attached shortest path (validated if present).
        playable: Whether the spec v2.2 "playable Pac-Man board" rules apply
            (open corners/centre, at least two loops, rare dead ends). This is
            opt-in: the output-file CLI leaves it off because a file does not
            record the intended mode.

    Returns:
        A list of problem messages. Empty means all conditions are satisfied.
    """
    reserved = reserved if reserved is not None else set()
    problems: List[str] = []
    problems += _check_endpoints(maze, entry, exit_)
    if problems:
        return problems  # if endpoints are invalid, nothing else matters
    problems += _check_border(maze)
    problems += _check_wall_consistency(maze)
    problems += _check_connectivity(maze, entry, reserved)
    problems += _check_no_open_3x3(maze)
    if perfect:
        problems += _check_perfect(maze, reserved)
    if playable:
        problems += _check_playable(maze, entry, reserved)
    if solution is not None:
        problems += _check_solution(maze, entry, exit_, solution)
    return problems


def _parse_output_file(path: str) -> Tuple[Maze, Coord, Coord, str]:
    """Read an output file (spec IV.5 format) and reconstruct the maze/endpoints/path."""
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    # Drop one trailing blank line (from the final \n).
    if lines and lines[-1] == "":
        lines.pop()
    # Everything up to the first blank line is the hex grid.
    grid_lines: List[str] = []
    idx = 0
    while idx < len(lines) and lines[idx] != "":
        grid_lines.append(lines[idx])
        idx += 1
    if idx + 3 > len(lines):
        raise ValueError("malformed output file (missing meta lines)")
    entry_s, exit_s, path = lines[idx + 1], lines[idx + 2], lines[idx + 3]

    height = len(grid_lines)
    width = len(grid_lines[0]) if grid_lines else 0
    cells: List[List[int]] = []
    for row in grid_lines:
        if len(row) != width:
            raise ValueError("hex grid rows have inconsistent width")
        cells.append([int(ch, 16) for ch in row])
    maze = Maze(width, height, cells)

    def coord(s: str) -> Coord:
        a, b = s.split(",")
        return (int(a), int(b))

    return maze, coord(entry_s), coord(exit_s), path


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point. Validate an output file and print the result."""
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print("usage: python -m engine.validator <output_file>")
        return 2
    try:
        maze, entry, exit_, path = _parse_output_file(args[0])
    except (OSError, ValueError) as err:
        print(f"read error: {err}")
        return 2

    # An output file does not record reserved cells / perfect, so validate
    # structure only.
    problems = validate(maze, entry, exit_, solution=path)
    if problems:
        print(f"FAIL: {len(problems)} problem(s)")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("OK: the maze satisfies the structural conditions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
