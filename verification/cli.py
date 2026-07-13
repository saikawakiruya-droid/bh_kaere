"""Standalone CLI: validate a spec IV.5 output file from disk.

``python -m verification.cli <output_file>`` reads an output file written by
``a_maze_ing.py`` and reconstructs the :class:`~core.maze.Maze` plus
entry/exit/solution from it, then runs :func:`verification.verifier.validate`
against it. The CLI validates structure only (an output file does not record
whether the maze was meant to be ``PERFECT`` or "playable"), unlike the main
pipeline, which passes those flags directly.
"""

from __future__ import annotations

import sys
from typing import List, Optional, Tuple

from core.maze import Maze
from verification.verifier import validate

Coord = Tuple[int, int]


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
    # Need lines[idx+3] (the path line) to exist, i.e. len(lines) >= idx + 4.
    # The old `idx + 3` guard was off-by-one: a file missing only the path line
    # passed the check and then raised an uncaught IndexError below.
    if idx + 4 > len(lines):
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
        print("usage: python -m verification.cli <output_file>")
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
