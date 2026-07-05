# A-Maze-ing Makefile
#
# Main targets: install / run / debug / clean / lint / lint-strict / test
#
# The Python used can be overridden via the PYTHON variable. Example:
#   make run PYTHON=python3.11 CONFIG=config.txt

PYTHON ?= python3
CONFIG ?= config.txt

MYPY_FLAGS = --warn-return-any --warn-unused-ignores \
             --ignore-missing-imports --disallow-untyped-defs \
             --check-untyped-defs

.PHONY: install run debug test lint lint-strict clean

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install flake8 mypy pytest

run:
	$(PYTHON) a_maze_ing.py $(CONFIG)

debug:
	$(PYTHON) -m pdb a_maze_ing.py $(CONFIG)

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m flake8 .
	$(PYTHON) -m mypy . $(MYPY_FLAGS)

lint-strict:
	$(PYTHON) -m flake8 .
	$(PYTHON) -m mypy . --strict

clean:
	rm -rf .mypy_cache .pytest_cache *.egg-info build dist
	find . \( -path ./.venv -o -path ./.git \) -prune -o \
	       -type d -name __pycache__ -exec rm -rf {} +
	rm -f maze.txt o.txt
