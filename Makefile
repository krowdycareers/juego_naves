VENV := .venv
PYTHON ?= $(VENV)/bin/python
PIP ?= $(VENV)/bin/pip
PROJECT_CACHE := .cache
MPLCONFIGDIR := $(PROJECT_CACHE)/matplotlib
XDG_CACHE_HOME := $(PROJECT_CACHE)

.PHONY: setup install start start-no-interactive test-init

setup:
	python3 -m venv $(VENV)
	mkdir -p $(MPLCONFIGDIR)
	$(PIP) install -r requirements.txt

install: setup

start:
	mkdir -p $(MPLCONFIGDIR)
	MPLCONFIGDIR=$(MPLCONFIGDIR) XDG_CACHE_HOME=$(XDG_CACHE_HOME) $(PYTHON) main.py

start-no-interactive:
	mkdir -p $(MPLCONFIGDIR)
	MPLCONFIGDIR=$(MPLCONFIGDIR) XDG_CACHE_HOME=$(XDG_CACHE_HOME) $(PYTHON) main.py --no-interactive

test-init:
	mkdir -p $(MPLCONFIGDIR)
	MPLCONFIGDIR=$(MPLCONFIGDIR) XDG_CACHE_HOME=$(XDG_CACHE_HOME) PYTHONPATH=. $(PYTHON) tests/test_init_only.py
