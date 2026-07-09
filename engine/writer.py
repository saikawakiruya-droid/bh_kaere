"""Write the maze in the spec IV.5 output-file format.

Format:

- Each cell is a single upper-case hex digit (closed walls encoded as bits:
  bit0=north, bit1=east, bit2=south, bit3=west; 1 means the wall is closed).
  The :class:`~engine.maze.Maze` wall codes already match this layout, so the
  value is simply turned into hex.
- One line of cells per row.
- One blank line, then 3 lines:
  entry ``x,y`` / exit ``x,y`` / shortest path (``N``/``E``/``S``/``W``).
- Every line ends with ``\\n``.

Standalone usage::

    from engine.maze import Maze
    from engine.writer import write_maze

    maze = Maze(5, 5)
    write_maze("maze.txt", maze, entry=(0, 0), exit_=(4, 4), solution="EESS")
"""

from __future__ import annotations

from typing import Optional, Tuple

from engine.errors import MazeError
from engine.maze import Maze

Coord = Tuple[int, int]


def format_maze(maze: Maze, entry: Coord, exit_: Coord,
                solution: Optional[str]) -> str:
    """Build the output-file content (including the trailing newline) as a string.

    Args:
        maze: The maze to output.
        entry: Entry coordinate ``(x, y)``.
        exit_: Exit coordinate ``(x, y)``.
        solution: The shortest path from entry to exit (``N``/``E``/``S``/``W``).
            If unreachable and ``None``, written as a blank line.

    Returns:
        A string where every line is newline-terminated, joined with ``\\n``.
    """
    rows = [
        "".join(format(maze.cells[y][x], "X") for x in range(maze.width))
        for y in range(maze.height)
    ]
    lines = rows + [
        "",
        f"{entry[0]},{entry[1]}",
        f"{exit_[0]},{exit_[1]}",
        solution if solution is not None else "",
    ]
    # Terminate every line with \n (including the last one).
    return "".join(line + "\n" for line in lines)


def write_maze(path: str, maze: Maze, entry: Coord, exit_: Coord,
               solution: Optional[str]) -> None:
    """Write the maze to ``path`` in the output-file format.

    Args:
        path: Destination file path.
        maze: The maze to output.
        entry: Entry coordinate.
        exit_: Exit coordinate.
        solution: The shortest path string.

    Raises:
        MazeError: If writing the file fails.
    """
    content = format_maze(maze, entry, exit_, solution)
    try:
        # newline="" suppresses OS newline translation, so we always write \n.
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(content)
    except OSError as err:
        raise MazeError(f"cannot write output file: {path} ({err})")
