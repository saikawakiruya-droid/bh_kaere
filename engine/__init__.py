"""The maze engine: build, validate, and output a maze — usable in parts.

Each stage lives in its own module and can be imported on its own (see that
module's docstring for a copy-pasteable example): :mod:`engine.maze` (core data
structure), :mod:`engine.initializer` ("42" sign reservation + initial map),
:mod:`engine.backtracker` (the recursive-backtracker algorithm),
:mod:`engine.generator` (algorithm selection registry),
:mod:`engine.braiding` (imperfect-maze / playable-board conversion),
:mod:`engine.metrics` (loop / dead-end counting),
:mod:`engine.validator` (spec IV.4 condition checks), :mod:`engine.writer`
(output-file writing), :mod:`engine.ascii_display` (ASCII rendering), and
:mod:`engine.display` (display-mode selection registry).

Basic usage (the full pipeline, PERFECT=False)::

    import random
    from engine import (
        initialize_maze, generate_backtracker, braid, solve, validate,
        write_maze, render_ascii,
    )

    rng = random.Random(42)
    entry, exit_ = (0, 0), (19, 14)
    _, reserved = initialize_maze(20, 15, entry=entry, exit_=exit_)
    maze = generate_backtracker(20, 15, reserved, rng, start=entry)
    braid(maze, reserved, rng, min_loops=2)

    solution = solve(maze, entry, exit_)
    problems = validate(maze, entry, exit_, reserved=reserved,
                        solution=solution, playable=True)

    write_maze("maze.txt", maze, entry, exit_, solution)
    print(render_ascii(maze, entry=entry, exit_=exit_))
"""

from __future__ import annotations

import importlib
from typing import Any, Dict

# name -> the submodule that defines it. Resolved lazily by __getattr__
# (PEP 562) instead of importing every submodule eagerly at package-import
# time: eager imports here would make each submodule already present in
# ``sys.modules`` under ``engine.*``, which triggers a RuntimeWarning when a
# submodule with its own CLI (e.g. ``engine.validator``) is run directly with
# ``python -m engine.validator``.
_SUBMODULE_OF: Dict[str, str] = {
    "GLYPHS": "engine.initializer",
    "initialize_maze": "engine.initializer",
    "reserved_cells": "engine.initializer",
    "sign_bitmap": "engine.initializer",
    "generate_backtracker": "engine.backtracker",
    "algorithm_names": "engine.generator",
    "get_algorithm": "engine.generator",
    "braid": "engine.braiding",
    "count_dead_ends": "engine.metrics",
    "count_loops": "engine.metrics",
    "ConfigError": "engine.errors",
    "ConfigKeyError": "engine.errors",
    "ConfigParseError": "engine.errors",
    "ConfigValueError": "engine.errors",
    "MazeError": "engine.errors",
    "SignError": "engine.errors",
    "SignOverlapError": "engine.errors",
    "SignTooBigError": "engine.errors",
    "DIRECTIONS": "engine.maze",
    "Maze": "engine.maze",
    "bfs_distances": "engine.maze",
    "path_to_cells": "engine.maze",
    "solution_cells": "engine.maze",
    "solve": "engine.maze",
    "format_maze": "engine.writer",
    "write_maze": "engine.writer",
    "WALL_COLORS": "engine.ascii_display",
    "render_ascii": "engine.ascii_display",
    "display_names": "engine.display",
    "get_display_mode": "engine.display",
    "validate": "engine.validator",
}

__all__ = sorted(_SUBMODULE_OF)


def __getattr__(name: str) -> Any:
    """Lazily resolve a re-exported name from its submodule (PEP 562)."""
    try:
        module_name = _SUBMODULE_OF[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(importlib.import_module(module_name), name)
