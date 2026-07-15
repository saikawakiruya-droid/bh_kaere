"""Library-side maze verification: checks whether a maze satisfies spec IV.4.

Call :func:`validate` right after generation to get the list of problems
(empty means valid). The main pipeline uses this to confirm post-generation
that "a compliant maze was produced". This is distinct from *validation*
(:mod:`validation.config` / :mod:`validation.options`), which checks the
config-file *input* before a maze is even built — this module *verifies* the
already-built maze's structure instead.

For the standalone CLI (``python -m verification.cli <output_file>``, which
reads an output file and calls :func:`validate` on it), see :mod:`verification.cli`.

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

    from core.maze import Maze
    from verification.verifier import validate

    maze = Maze(5, 5)
    problems = validate(maze, entry=(0, 0), exit_=(4, 4))
    if problems:
        print(f"{len(problems)} problem(s):", *problems, sep="\n  - ")
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from core.maze import (
    DIRECTIONS,
    OPPOSITE,
    WALL_E,
    WALL_N,
    WALL_S,
    WALL_W,
    Maze,
    bfs_distances,
    playable_corridors,
)
from core.metrics import count_dead_ends, count_loops

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


def _check_connectivity(maze: Maze, entry: Coord, reserved: Set[Coord],
                        entry_dist: Dict[Coord, int]) -> List[str]:
    """Check that non-reserved cells are connected and reserved cells are closed.

    The reserved cells of the "42" sign are isolated cells closed on all four
    sides (``0xF``), which is an exception allowed by the spec.

    When ``reserved`` is known (non-empty, the generation-side case), only those
    cells are treated as allowed isolation, so any *other* fully closed
    ``0xF`` cell counts as a genuine isolation error, and it is also checked
    that the reserved cells really are all closed.

    When ``reserved`` is empty (the output-file case, where the file does not
    record the reserved cells), every ``0xF`` cell is treated as reserved
    (allowed isolation) and excluded from the connectivity check, preserving
    the original behaviour.
    """
    problems: List[str] = []
    for (x, y) in reserved:
        if maze.cells[y][x] != 0xF:
            problems.append(f"reserved cell is open: ({x},{y})")

    if reserved:
        # Reserved set known: only those cells are allowed to be isolated;
        # any other 0xF cell falls into ``free`` and, being unreachable, is
        # reported as an isolated cell.
        closed = set(reserved)
    else:
        # Output-file case: the reserved set is unknown, so every fully closed
        # cell (the 42 sign) is treated as allowed isolation.
        closed = {(x, y) for y in range(maze.height) for x in range(maze.width)
                  if maze.cells[y][x] == 0xF}
    free = {(x, y) for y in range(maze.height) for x in range(maze.width)
            if (x, y) not in closed}
    if entry in closed:
        problems.append(f"entry sits on a fully closed cell: {entry}")
        return problems
    reachable = set(entry_dist.keys())
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


def _check_playable(maze: Maze, reserved: Set[Coord],
                    entry_dist: Dict[Coord, int]) -> List[str]:
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
    reachable: Set[Coord] = set(entry_dist.keys())
    for (x, y) in sorted(playable_corridors(maze.width, maze.height)):
        if (x, y) in reserved or maze.cells[y][x] == 0xF:
            problems.append(
                f"corner/centre is closed, not an open corridor: ({x},{y})"
            )
        elif (x, y) not in reachable:
            problems.append(f"corner/centre is not reachable: ({x},{y})")
        elif maze.count_openings(x, y) < 2:
            problems.append(
                f"corner/centre is a dead end, not an open corridor: "
                f"({x},{y}) has {maze.count_openings(x, y)} opening(s)"
            )

    # At least two independent loops (a perfect maze, or one with a single
    # removed wall, is not acceptable).
    free_count = maze.width * maze.height - len(reserved)
    if free_count > 0:
        loops = count_loops(maze, reserved)
        if loops < 2:
            # count_loops uses edges - vertices + 1, which can go negative on a
            # disconnected free region; clamp the reported figure to 0 so the
            # message never shows a nonsensical negative loop count.
            problems.append(
                f"playable board needs at least 2 independent loops, "
                f"found {max(0, loops)}"
            )

    # Dead ends should be rare (a couple are tolerated; zero is the bonus).
    dead = count_dead_ends(maze, reserved)
    threshold = 2
    if dead > threshold:
        problems.append(
            f"too many dead ends for a playable board: {dead} "
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
                    solution: Optional[str],
                    entry_dist: Dict[Coord, int]) -> List[str]:
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
    dist = entry_dist.get(exit_)
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
    # Single entry-origin BFS shared by every check that needs reachability /
    # distances from the entry (connectivity, playable corridors, solution).
    entry_dist = bfs_distances(maze, entry)
    problems += _check_border(maze)
    problems += _check_wall_consistency(maze)
    problems += _check_connectivity(maze, entry, reserved, entry_dist)
    problems += _check_no_open_3x3(maze)
    if perfect:
        problems += _check_perfect(maze, reserved)
    if playable:
        problems += _check_playable(maze, reserved, entry_dist)
    if solution is not None:
        problems += _check_solution(maze, entry, exit_, solution, entry_dist)
    return problems
