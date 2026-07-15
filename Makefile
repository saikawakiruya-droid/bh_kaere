# A-Maze-ing Makefile
#
# Main targets: install / run / debug / clean / lint / lint-strict / test
#
# `make install` builds an isolated virtual environment in ./.venv and
# installs the dev tools there (prefers `uv`, falls back to `python -m venv`).
# All other targets run through that venv's interpreter, so the host Python
# is never touched. If ./.venv does not exist yet, they fall back to an
# available system Python, so `make run` still works without `make install`.
#
# Design goal: PY_VERSION is the PREFERRED version, never a hard requirement.
# The pinned version is used when available (and uv auto-fetches it), but on a
# machine without it the build gracefully falls back to any available python3,
# so `make` works in ANY environment. A Python < 3.10 only prints a warning.
#
# Overridable variables:
#   PY_VERSION  preferred Python version for the venv (default: 3.12). With uv
#               it is auto-fetched; otherwise python$(PY_VERSION) is used if
#               present, else it falls back to the system python3.
#   PYTHON      bootstrap interpreter for the stdlib-venv path and the
#               no-venv fallback. Auto-resolved (python$(PY_VERSION) if it
#               exists, else python3); override for a custom path.
#   CONFIG      config file passed to the program (default: config.txt)
# Examples:
#   make install                  # prefer Python 3.12, fall back if absent
#   make install PY_VERSION=3.11  # prefer a different version
#   make run CONFIG=my_config.txt

PY_VERSION ?= 3.12
CONFIG     ?= config.txt
ANALYZER   ?= maze_analyzer.py
OUTPUT      = $(shell awk -F= '/^[[:space:]]*OUTPUT_FILE[[:space:]]*=/{gsub(/[[:space:]]/,"",$$2); print $$2}' $(CONFIG))

VENV     = .venv
VENV_PY  = $(VENV)/bin/python
# Bootstrap interpreter: prefer the pinned version, else fall back to any
# available python3 (guarantees `make` runs even without the pinned version).
PYTHON   ?= $(shell command -v python$(PY_VERSION) 2>/dev/null || \
                    command -v python3 2>/dev/null || echo python3)
# Use the venv interpreter once it exists, otherwise the bootstrap PYTHON.
PY       = $(shell [ -x "$(VENV_PY)" ] && echo "$(VENV_PY)" || echo "$(PYTHON)")

MYPY_FLAGS = --warn-return-any --warn-unused-ignores \
             --ignore-missing-imports --disallow-untyped-defs \
             --check-untyped-defs

.PHONY: install run debug test lint lint-strict analyze analyze-bonus clean distclean

# Create an isolated environment and install the dev tools into it.
# Prefer uv (fast); fall back to the stdlib venv + pip when uv is absent.
install:
	@if command -v uv >/dev/null 2>&1; then \
		echo ">> uv found: creating $(VENV) (prefer Python $(PY_VERSION), auto-fetched if needed)"; \
		uv venv --python $(PY_VERSION) $(VENV) 2>/dev/null || { \
			echo ">> Python $(PY_VERSION) unavailable; falling back to uv's default Python"; \
			uv venv $(VENV); \
		}; \
		uv pip install --python $(VENV_PY) flake8 mypy pytest; \
	else \
		echo ">> uv not found; using '$(PYTHON) -m venv'"; \
		$(PYTHON) -m venv $(VENV); \
		$(VENV_PY) -m pip install --upgrade pip; \
		$(VENV_PY) -m pip install flake8 mypy pytest; \
	fi
	@$(VENV_PY) -c 'import sys; v=sys.version_info; print(f">> environment ready: Python {v.major}.{v.minor}.{v.micro}"); \
		(v[:2] >= (3, 10)) or sys.stderr.write(">> WARNING: Python < 3.10; the subject requires >= 3.10\n")'

run:
	$(PY) a_maze_ing.py $(CONFIG)

debug:
	$(PY) -m pdb a_maze_ing.py $(CONFIG)

test:
	$(PY) -m pytest -q

lint:
	$(PY) -m flake8 .
	$(PY) -m mypy . $(MYPY_FLAGS)

lint-strict:
	$(PY) -m flake8 .
	$(PY) -m mypy . --strict

clean:
	rm -rf .mypy_cache .pytest_cache *.egg-info build dist
	find . \( -path ./.venv -o -path ./.git \) -prune -o \
	       -type d -name __pycache__ -exec rm -rf {} +
	rm -f maze.txt o.txt

# Remove the virtual environment as well (kept out of `clean` so day-to-day
# cleaning does not force a full reinstall).
distclean: clean
	rm -rf $(VENV)

# Generate the maze from CONFIG, then judge it with the official
# maze_analyzer.py. Non-interactive (< /dev/null) so no menu opens.
analyze:
	$(PY) a_maze_ing.py $(CONFIG) < /dev/null
	@echo ">> analyzing $(OUTPUT) with the official maze_analyzer.py"
	$(PY) $(ANALYZER) $(OUTPUT)

# Same, but require ZERO real dead-ends (the no-dead-end bonus check).
analyze-bonus:
	$(PY) a_maze_ing.py $(CONFIG) < /dev/null
	$(PY) $(ANALYZER) $(OUTPUT) --max-dead-ends 0
