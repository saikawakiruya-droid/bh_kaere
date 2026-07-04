"""A-Maze-ing — the main program of the maze generator.

Usage::

    python a_maze_ing.py config.txt

Reads a config file, generates a (optionally perfect) maze, and writes it to a
file in the spec IV.5 hex format. After generation it confirms the conditions
with :mod:`validator`, and finally renders the maze to the terminal.

It handles all errors gracefully and never crashes unexpectedly. On any
problem it prints a clear message and returns an exit code.
"""

from __future__ import annotations

import random
import sys
from typing import List, Optional, Set, Tuple

from braiding import braid
from config import Config, parse_config
from display import WALL_COLORS, get_display_mode
from errors import MazeError
from generator import get_algorithm
from initializer import initialize_maze
from maze import Maze, solution_cells, solve
from validator import validate
from writer import write_maze

Coord = Tuple[int, int]


def build_maze(config: Config) -> Tuple[Maze, Set[Coord]]:
    """Build the maze from the config (init -> reserve sign -> generate -> braid).

    When ``PERFECT=False``, braiding runs after generation to reduce dead ends
    and create loops (multiple paths), while keeping passages at most 2 cells
    wide.

    Args:
        config: The validated configuration.

    Returns:
        ``(maze, reserved)``, where ``reserved`` is the "42" reserved-cell set.
    """
    rng = random.Random(config.options.seed)
    _, reserved = initialize_maze(
        config.width, config.height,
        entry=config.entry, exit_=config.exit,
        sign=config.options.sign)
    generate = get_algorithm(config.options.algorithm)
    maze = generate(config.width, config.height, reserved, rng, config.entry)
    if not config.perfect:
        braid(maze, reserved, rng)
    return maze, reserved


def run(config_path: str) -> int:
    """Process the config file: generate, validate, write, and display the maze.

    Args:
        config_path: Path to the config file.

    Returns:
        Exit code (0 = success, 1 = error).
    """
    try:
        config = parse_config(config_path)
    except MazeError as err:
        print(f"config error: {err}", file=sys.stderr)
        return 1

    try:
        maze, reserved = build_maze(config)
    except MazeError as err:
        print(f"generation error: {err}", file=sys.stderr)
        return 1

    solution = solve(maze, config.entry, config.exit)

    # Confirm post-generation that the conditions hold (spec IV.4).
    problems = validate(maze, config.entry, config.exit,
                        reserved=reserved, perfect=config.perfect,
                        solution=solution)
    if problems:
        print(f"warning: the generated maze fails {len(problems)} condition(s):",
              file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)

    try:
        write_maze(config.output_file, maze, config.entry, config.exit,
                   solution)
    except MazeError as err:
        print(f"output error: {err}", file=sys.stderr)
        return 1
    print(f"wrote output file: {config.output_file}")

    path_cells = solution_cells(maze, config.entry, config.exit)
    render = get_display_mode(config.options.display)
    print(render(maze, entry=config.entry, exit_=config.exit,
                 path=path_cells, reserved=reserved, show_path=True))

    # Offer interaction only when running interactively in a terminal
    # (skip for pipes and other non-interactive runs so we do not hang).
    if sys.stdin.isatty() and sys.stdout.isatty():
        interact(config, maze, reserved)
    return 0


def interact(config: Config, maze: Maze, reserved: Set[Coord]) -> None:
    """Simple terminal interaction (spec V).

    - 1: regenerate a new maze and display it (seed auto +1)
    - 2: regenerate with a specified seed value
    - 3: toggle the shortest-path display
    - 4: change the wall color
    - 5: quit

    Args:
        config: The configuration (used while varying the seed on regenerate).
        maze: The current maze.
        reserved: The "42" reserved-cell set.
    """
    render = get_display_mode(config.options.display)
    color_names = list(WALL_COLORS)
    color_idx = 0
    show_path = True
    seed = config.options.seed if config.options.seed is not None else 0

    def show() -> None:
        path_cells = solution_cells(maze, config.entry, config.exit)
        print(render(maze, entry=config.entry, exit_=config.exit,
                     path=path_cells, reserved=reserved,
                     show_path=show_path,
                     wall_color=WALL_COLORS[color_names[color_idx]]))

    def regenerate() -> None:
        nonlocal maze, reserved
        try:
            maze, reserved = build_maze(config)
        except MazeError as err:
            print(f"regeneration error: {err}", file=sys.stderr)
            return
        show()

    while True:
        print("\n=== A-Maze-ing ===")
        print(f"1. Regenerate a new maze (next seed: {seed + 1})")
        print("2. Regenerate with a specified seed")
        print("3. Toggle the shortest-path display")
        print(f"4. Change the wall color (current: {color_names[color_idx]})")
        print(f"5. Quit (current seed: {seed})")
        try:
            choice = input("choice (1-5): ").strip()
        except EOFError:
            return

        if choice == "1":
            seed += 1
            config.options.seed = seed
            regenerate()
        elif choice == "2":
            try:
                raw = input("seed value (integer): ").strip()
            except EOFError:
                return
            try:
                seed = int(raw)
            except ValueError:
                print("Please enter an integer.")
                continue
            config.options.seed = seed
            regenerate()
        elif choice == "3":
            show_path = not show_path
            show()
        elif choice == "4":
            color_idx = (color_idx + 1) % len(color_names)
            show()
        elif choice == "5":
            return
        else:
            print("Please enter 1-5.")


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point."""
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print("usage: python a_maze_ing.py <config_file>", file=sys.stderr)
        return 2
    try:
        return run(args[0])
    except Exception as err:  # never crash, even on the unexpected.
        print(f"unexpected error: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
