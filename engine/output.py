"""Get a maze out of the program: file output and terminal display.

Two independent stages live here — use either one on its own:

1. **File output** (``format_maze`` / ``write_maze``) — spec IV.5 hex format.
2. **Terminal display** (``render_ascii``) — ASCII-art rendering.

Standalone usage (file output only)::

    from engine.maze import Maze
    from engine.output import write_maze

    maze = Maze(5, 5)
    write_maze("maze.txt", maze, entry=(0, 0), exit_=(4, 4), solution="EESS")

Standalone usage (terminal display only)::

    from engine.maze import Maze
    from engine.output import render_ascii

    maze = Maze(5, 5)
    print(render_ascii(maze, entry=(0, 0), exit_=(4, 4)))
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Set, Tuple

from engine.errors import ConfigValueError, MazeError
from engine.maze import WALL_N, WALL_S, WALL_W, Maze

Coord = Tuple[int, int]

# ===========================================================================
# 1. File output (spec IV.5 output-file format)
# ===========================================================================
#
# Format:
#
# - Each cell is a single upper-case hex digit (closed walls encoded as bits:
#   bit0=north, bit1=east, bit2=south, bit3=west; 1 means the wall is closed).
#   The :class:`~engine.maze.Maze` wall codes already match this layout, so the
#   value is simply turned into hex.
# - One line of cells per row.
# - One blank line, then 3 lines:
#   entry ``x,y`` / exit ``x,y`` / shortest path (``N``/``E``/``S``/``W``).
# - Every line ends with ``\n``.


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
        A string where every line is newline-terminated, joined with ``\n``.
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


# ===========================================================================
# 2. Terminal display and display-mode selection registry
# ===========================================================================
#
# Currently the only display mode is **terminal ASCII**, but a mechanism to
# select it via the ``DISPLAY`` config key is provided from the start (to add
# e.g. MLX later, just register it in ``DISPLAY_MODES``).

RendererFn = Callable[..., str]

# ANSI colors selectable as the wall color (toggled during interaction).
RESET = "\033[0m"
WALL_COLORS: Dict[str, str] = {
    "none": "",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
}
SIGN_COLOR = "\033[1;33m"   # "42" sign (bold yellow)
PATH_COLOR = "\033[1;32m"   # solution path (bold green)


def _paint(text: str, color: str) -> str:
    """Wrap ``text`` in an ANSI color if ``color`` is non-empty."""
    return f"{color}{text}{RESET}" if color else text


def _body(cell: Coord, entry: Optional[Coord], exit_: Optional[Coord],
          path: Set[Coord], reserved: Set[Coord], color: bool) -> str:
    """Return the 3-character body shown at the center of a cell."""
    if cell in reserved:
        return _paint("###", SIGN_COLOR) if color else "###"
    if cell == entry:
        return " E "
    if cell == exit_:
        return " X "
    if cell in path:
        return _paint(" * ", PATH_COLOR) if color else " * "
    return "   "


def render_ascii(maze: Maze,
                 entry: Optional[Coord] = None,
                 exit_: Optional[Coord] = None,
                 path: Optional[Set[Coord]] = None,
                 reserved: Optional[Set[Coord]] = None,
                 show_path: bool = True,
                 wall_color: str = "") -> str:
    """Render the maze as an ASCII-art string.

    Walls are drawn with ``+``, ``-`` and ``|``; the entry as ``E``, the exit
    as ``X``, the solution path as ``*``, and the reserved cells of the "42"
    sign as ``#``. Passing an ANSI code from ``WALL_COLORS`` as ``wall_color``
    colors the walls (default is uncolored).

    Args:
        maze: The maze to render.
        entry: Entry coordinate.
        exit_: Exit coordinate.
        path: Set of cells on the solution path (shown when ``show_path``).
        reserved: Set of reserved cells of the "42" sign.
        show_path: Whether to show the path.
        wall_color: ANSI color code applied to walls (empty = uncolored).

    Returns:
        The rendered string, including newlines.
    """
    shown_path = path if (show_path and path is not None) else set()
    reserved = reserved if reserved is not None else set()
    color = bool(wall_color)
    w, h = maze.width, maze.height

    def hbar(x: int, y: int, bit: int) -> str:
        seg = "+" + ("---" if maze.has_wall(x, y, bit) else "   ")
        return _paint(seg, wall_color) if color else seg

    lines: List[str] = []
    for y in range(h):
        # North wall (top border line) of each cell.
        top = "".join(hbar(x, y, WALL_N) for x in range(w))
        top += _paint("+", wall_color) if color else "+"
        lines.append(top)
        # West wall + body of each cell.
        mid = ""
        for x in range(w):
            if maze.has_wall(x, y, WALL_W):
                mid += _paint("|", wall_color) if color else "|"
            else:
                mid += " "
            mid += _body((x, y), entry, exit_, shown_path, reserved, color)
        mid += _paint("|", wall_color) if color else "|"  # right outer border
        lines.append(mid)
    # South wall (bottom border line) of the last row.
    bottom = "".join(hbar(x, h - 1, WALL_S) for x in range(w))
    bottom += _paint("+", wall_color) if color else "+"
    lines.append(bottom)
    return "\n".join(lines)


# --- Display-mode selection registry -------------------------------------
DISPLAY_MODES: Dict[str, RendererFn] = {
    "ascii": render_ascii,
}


def display_names() -> List[str]:
    """Return the available display-mode names in ascending order."""
    return sorted(DISPLAY_MODES)


def get_display_mode(name: str) -> RendererFn:
    """Look up a renderer function by name.

    Args:
        name: Display-mode name (the ``DISPLAY`` config value).

    Returns:
        The corresponding renderer function.

    Raises:
        ConfigValueError: If the display-mode name is unknown.
    """
    try:
        return DISPLAY_MODES[name]
    except KeyError:
        raise ConfigValueError(
            f"unknown display mode '{name}'. choices: {display_names()}"
        )
