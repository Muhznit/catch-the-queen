#!/usr/bin/env -S make -f
.PHONY: help install run clean unittest ship
PYTHON_EXE=./venv/Scripts/python.exe

help: ## You are here
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'

venv:
	py.exe -m venv venv

install: venv
	$(PYTHON_EXE) -m pip install -r requirements.txt

run: venv ## Run the actual program
	@$(PYTHON_EXE) main.py

clean-pyc: 
	@find . -type d -name '__pycache__' -exec rm -rf {} +
	@find . -type f -name '*.py[co]' -exec rm -f {} +

clean: clean-pyc ## Remove python file artifacts and clutter

unittest: ## Run unit tests
	@$(PYTHON_EXE) -m unittest -v > /dev/null

ship: ## Push new version, tbd
