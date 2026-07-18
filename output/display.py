"""Selection registry for maze display modes.

The display mode is selected via the ``DISPLAY`` config key. Currently the only
choice is **terminal ASCII** (:func:`output.ascii_display.render_ascii`).

Standalone usage::

    from output.display import get_display_mode

    render = get_display_mode("ascii")
    print(render(maze, entry=(0, 0), exit_=(4, 4)))
"""

from __future__ import annotations

from typing import Callable, Dict, List

from core.errors import ConfigValueError
from output.ascii_display import render_ascii

RendererFn = Callable[..., str]

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
    except KeyError as err:
        raise ConfigValueError(
            f"unknown display mode '{name}'. choices: {display_names()}"
        ) from err
