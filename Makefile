
#### Before doing anything else: if on Windows set SHELL ####
# Use Git "bash" instead of Git "sh" like so:

ifeq ($(OS),Windows_NT)
SHELL = $(shell which bash)
@echo "Using shell: $(info $(SHELL))"
PYTHON_INTERPRETER = python
else # if on Linux/OSX try bash
SHELL = /bin/bash
@echo "Using shell: $(info $(SHELL))"
PYTHON_INTERPRETER = python
endif


.PHONY: clean data lint requirements setup update export help


######################
#### List globals ####
######################

PROJECT_NAME = patentpack
PYTHON_VERSION = 3.12

# Check if conda exists
ifeq (,$(shell ! command -v conda &> /dev/null))
HAS_CONDA=True
else
HAS_CONDA=False
endif

# Check if poetry exists
ifeq (,$(shell ! command -v poetry &> /dev/null))
HAS_POETRY=True
else
HAS_POETRY=False
endif


##############################
#### Setup / Dependencies ####
##############################

#### List dependencies and packages ####

# Development dependencies
DEVPCKGS := coverage pynvim pytest pytest-cov python-dotenv black isort flake8
# Standard dependencies
PCKGS := packaging toml

# Optional packages
EXTRAS :=

#### Setup recipes ####

## Bump project semantinc version with poetry
bump-version:
	@if [ -z "$(type)" ]; then \
		echo "Error: type argument is required"; \
		exit 1; \
	fi
	@poetry version $(type)
	@python scripts/update_version.py
	@echo "Version bumped ($(type)) and synced."

## Sync package semantic version manually
sync-version:
	@python scripts/update_version.py
	@echo "Version synced to __init__.py"

## Lock current dependencies
lock: pyproject.toml
		@echo "Locking dependencies without updating..."
		poetry lock --no-update

lock-update: poetry.lock
		@echo "Locking dependencies and updating..."
		poetry lock

## Install all dependencies and packages
setup-all: setup setup-dev setup-extras

## Install standard dependencies only
setup:
ifeq (True,$(HAS_POETRY))
		@echo "Poetry found, using Poetry to install standard dependencies"
		poetry install
		@echo "Installing standard dependencies..."
		$(foreach var,$(PCKGS),poetry add $(var);)
else
		@echo "Poetry not found, installing dependencies with pip"
		pip install -e
		$(foreach var,$(PCKGS),pip install $(var);)
		pip freeze > ./requirements.in
endif

## Install standard and development dependencies
setup-dev:
ifeq (True,$(HAS_POETRY))
		@echo "Poetry found, using Poetry to install development dependencies"
		@echo "Installing development dependencies..."
		poetry install
		$(foreach var,$(DEVPCKGS),poetry add -G dev $(var);)
else
		@echo "Poetry not found, installing development dependencies with pip"
		$(foreach var,$(DEVPCKGS),pip install $(var);)
		pip freeze > ./requirements-dev.in
endif

## Install non-dependencies
setup-extras:
ifeq (True,$(HAS_POETRY))
		@echo "Poetry found, using Poetry to install extras"
		@echo "Installing optional packages..."
		$(foreach var,$(EXTRAS),poetry add --optional $(var);)
else
		@echo "Poetry not found, installing extras with pip"
		$(foreach var,$(EXTRAS),pip install $(var);)
		pip freeze > ./requirements-extras.in
endif

## Install from an existing requirements.txt file
setup-reqs:
		poetry add `cat ./requirements.txt`

## Update all packages
update-all: update-dev update-extras

## Update standard dependencies (no dev or extras)
update:
ifeq (True,$(HAS_POETRY))
		@echo "Poetry found, using Poetry to update..."
		@echo "Updating standard dependencies..."
		poetry update --only main
else
		@echo "Poetry not found, updating packages with pip"
		touch ./requirements.in
		$(foreach var,$(PCKGS),pip install --upgrade $(var);)
		$(foreach var,$(PCKGS),$(var); >> ./requirements.in)
endif

## Update development dependencies
update-dev:
ifeq (True,$(HAS_POETRY))
		@echo "Poetry found, using Poetry to update..."
		@echo "Updating development dependencies..."
		poetry update
else
		@echo "Poetry not found, updating development dependencies with pip"
		touch ./requirements-dev.in
		$(foreach var,$(DEVPCKGS),pip install --upgrade $(var);)
		$(foreach var,$(DEVPCKGS),$(var); >> ./requirements-dev.in)
endif

## Update non-dependencies
update-extras:
ifeq (True,$(HAS_POETRY))
		@echo "Poetry found, using Poetry to update..."
		@echo "Updating optional packages..."
		$(foreach var,$(EXTRAS),poetry update $(var);)
else
		@echo "Poetry not found, updating extras with pip"
		touch ./requirements-extras.in
		$(foreach var,$(EXTRAS),pip install --upgrade $(var);)
		$(foreach var,$(EXTRAS),$(var); >> ./requirements-extras.in)
endif

## Make dependency tree
dep-tree:
ifeq (True,$(HAS_POETRY))
		@echo "Poetry found, using Poetry to make dependency tree"
		poetry show --tree > ./dep-tree.txt
else
		@echo "Poetry not found, making dependency tree with pip"
		pip freeze | sort > ./dep-tree.txt
endif

## Make project dirtree
tree:
		tree > ./dirtree.txt

######################
#### HOUSEKEEPING ####
######################

## Lint files in ./src using flake8
lint:
		flake8 src

## Format files and sort imports in ./src using black/isort
format-src:
		isort --profile black src
		black --line-length 79 src

## Format all files and sort imports
format:
		isort --profile black src
		isort --profile black .
		black --line-length 79 src
		black --line-length 79 .

## Delete all compiled Python files
clean:
		find . -type f -name "*.py[co]" -delete
		find . -type d -name "__pycache__" -delete


######################
#### Environments ####
######################

## Create fresh project environment
create-env:
ifeq (True,$(HAS_CONDA))
		@echo "Detected conda, creating conda environment."
		conda create --name $(PROJECT_NAME) python=$(PYTHON_VERSION)
else
		@echo "No conda detected, skipping conda environment creation."
		@echo "Check poetry env info for environment details."
endif

## Test if environment is setup correctly
test-env:
		$(PYTHON_INTERPRETER) ./scripts/check_environment.py

## Write QUARTO environment variables to .env
quarto:
		@echo "Exporting QUARTO environment variable to ./.env..."
		echo "QUARTO_PYTHON=$(shell poetry env info --path)" >> ./.env
		echo "QUARTO_PROJECT_DIR=./reports" >> ./.env
		@echo "Creating quarto project to the ./notebooks directory..."
		quarto create-project ./notebooks
		@echo "Setting output dir to ../reports/ ..."
		echo "  output-dir: ../reports" >> ./notebooks/_quarto.yml


###############
### Exports ###
###############

## Export dependencies in all formats
export: export-poet export-conda export-pip-tools

## Export poetry dependencies to a pip requirements.txt file
export-poet:
		@echo "Exporting poetry env to requirements.txt..."
		poetry export --dev -f requirements.txt --output ./requirements.txt

## Export conda env dependencies to an environment.yml file
export-conda:
		@echo "Exporting conda env to environment.yml..."
		conda env export --no-builds | grep -v "prefix" > ./environment.yml

## Export pip requirements directly to requirements.txt
export-pip:
		@echo "Exporting pip requirements to requirements.txt..."
		pip list --format=freeze > ./requirements.txt

## Export pip requirements with pip-tools (requires "requirements.in" file)
export-pip-tools:
		@echo "Exporting pip requirements.in to requirements.txt"
		pip-compile requirements.in


.DEFAULT_GOAL := help

# Inspired by <http://marmelab.com/blog/2016/02/29/auto-documented-makefile.html>
# sed script explained:
# /^##/:
# 	* save line in hold space
# 	* purge line
# 	* Loop:
# 		* append newline + line to hold space
# 		* go to next line
# 		* if line starts with doc comment, strip comment character off and loop
# 	* remove target prerequisites
# 	* append hold space (+ newline) to line
# 	* replace newline plus comments by `---`
# 	* print line
# Separate expressions are necessary because labels cannot be delimited by
# semicolon; see <http://stackoverflow.com/a/11799865/1968>
.PHONY: help
help:
	@echo "$$(tput bold)Available rules:$$(tput sgr0)"
	@echo
	@sed -n -e "/^## / { \
		h; \
		s/.*//; \
		:doc" \
		-e "H; \
		n; \
		s/^## //; \
		t doc" \
		-e "s/:.*//; \
		G; \
		s/\\n## /---/; \
		s/\\n/ /g; \
		p; \
	}" ${MAKEFILE_LIST} \
	| LC_ALL='C' sort --ignore-case \
	| awk -F '---' \
		-v ncol=$$(tput cols) \
		-v indent=19 \
		-v col_on="$$(tput setaf 6)" \
		-v col_off="$$(tput sgr0)" \
	'{ \
		printf "%s%*s%s ", col_on, -indent, $$1, col_off; \
		n = split($$2, words, " "); \
		line_length = ncol - indent; \
		for (i = 1; i <= n; i++) { \
			line_length -= length(words[i]) + 1; \
			if (line_length <= 0) { \
				line_length = ncol - indent - length(words[i]) - 1; \
				printf "\n%*s ", -indent, " "; \
			} \
			printf "%s ", words[i]; \
		} \
		printf "\n"; \
	}' \
	| more $(shell test $(shell uname) = Darwin && echo '--no-init --raw-control-chars')
