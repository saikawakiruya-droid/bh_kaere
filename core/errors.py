"""Exception hierarchy used across the whole project.

Errors are split into two families:

- ``ConfigError`` family (fatal): the configuration is invalid and **the maze
  cannot be created**. Callers print a message and terminate the program.
- ``SignError`` family (non-fatal): only the "42" sign cannot be placed, but
  **the maze itself can still be created**. Callers print a warning, omit the
  sign, and continue.

All of them share ``MazeError`` as a common base.
"""

from __future__ import annotations


class MazeError(Exception):
    """Base class for every exception in this project."""


# --- Configuration errors (fatal: the maze cannot be created) ------------
class ConfigError(MazeError):
    """Base class for problems with the configuration file."""


class ConfigParseError(ConfigError):
    """Syntax error (e.g. a line that is not ``KEY=VALUE``)."""


class ConfigKeyError(ConfigError):
    """A required key is missing. (Unknown keys are warnings, not fatal.)"""


class ConfigValueError(ConfigError):
    """A value is invalid (type, range, coordinate format, etc.)."""


# --- Sign errors (non-fatal: can continue by omitting the sign) ----------
class SignError(MazeError):
    """Base class for problems placing the "42" sign."""


class SignTooBigError(SignError):
    """The maze is too small for the sign to fit."""


class SignOverlapError(SignError):
    """The sign cannot be placed because it overlaps the entry or exit."""
