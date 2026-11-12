# ------------------------------------------------------------------------------
# OraDBA - Oracle Database Infrastructure and Security, 5630 Muri, Switzerland
# ------------------------------------------------------------------------------
# Name.......: Makefile
# Author.....: Stefan Oehrli (oes) stefan.oehrli@oradba.ch
# Editor.....: Stefan Oehrli
# Date.......: 12.11.2026
# Version....: v0.1.0
# Purpose....: Build the hold-my-beer frame deck (public / private) and run the
#              voting app locally (tests, start, stop).
# Notes......: Overrides via environment or .env. Use 'make help' for targets.
#              The private deck embeds photos - it is written outside the repo.
# Reference..: https://github.com/oehrlis/hold-my-beer
# License....: Apache License Version 2.0, January 2004 as shown
#              at http://www.apache.org/licenses/
# ------------------------------------------------------------------------------

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help
MAKEFLAGS += --no-builtin-rules
.SUFFIXES:

# Ensure Homebrew-installed tools are found regardless of caller's PATH
PATH := /opt/homebrew/bin:/usr/local/bin:$(PATH)
export PATH

# -- Colors --------------------------------------------------------------------
COLOR_RESET  := \033[0m
COLOR_BOLD   := \033[1m

# -- Project -------------------------------------------------------------------
PROJECT_NAME := hold-my-beer
EVENT        ?= doag-ak-2026
TALK_SLUG    ?= wissen-nicht-was-sie-tun

-include .env

# -- Directories ---------------------------------------------------------------
SLIDES_DIR := slides
APP_DIR    := app
VENV       := $(APP_DIR)/.venv
PYTHON     := $(VENV)/bin/python

# talks repo checkout with talks/$(TALK_SLUG)/talk.yaml (sibling of this repo)
TALKS_DIR  ?= $(abspath $(CURDIR)/../talks)
VOTING_URL ?= https://hmb.oradba.ch

# Private build: photos from OneDrive, deck written to OneDrive (never the repo)
CONF_DIR        ?= $(HOME)/Library/CloudStorage/OneDrive-Accenture/50_Community/Conferences/DOAG/2026-11-konferenz
HMB_PRIVATE_DIR ?= $(CONF_DIR)/media/hold-my-beer
PRIVATE_OUT     ?= $(CONF_DIR)/Own/$(TALK_SLUG).html

APP_PORT ?= 5000

# -- Tool detection ------------------------------------------------------------
SHELLCHECK   := $(shell PATH="$(PATH)" command -v shellcheck 2>/dev/null)
MARKDOWNLINT := $(shell PATH="$(PATH)" command -v markdownlint 2>/dev/null || \
                         PATH="$(PATH)" command -v markdownlint-cli 2>/dev/null)
TALK         := $(shell PATH="$(PATH)" command -v talk 2>/dev/null)
GIT          := $(shell PATH="$(PATH)" command -v git 2>/dev/null)

# Verbosity control (V=1 for verbose output)
V ?=
Q := $(if $(V),,@)

BUILD := VOTING_URL="$(VOTING_URL)" TALKS_DIR="$(TALKS_DIR)" EVENT="$(EVENT)" "$(SLIDES_DIR)/build.sh"

# ==============================================================================
# Help
# ==============================================================================

.PHONY: help
help: ## Show available targets
	@echo -e "$(COLOR_BOLD)$(PROJECT_NAME) Makefile$(COLOR_RESET)"
	@echo ""
	@echo "Typical flow:"
	@echo "  make deck            # public deck -> $(SLIDES_DIR)/$(EVENT)/$(TALK_SLUG).html (commit this one)"
	@echo "  make deck-private    # deck with private photos -> OneDrive (present this one)"
	@echo "  make app-test        # app tests before a deploy"
	@echo ""
	@echo -e "$(COLOR_BOLD)Deck$(COLOR_RESET)"
	@grep -E '^deck[a-zA-Z_-]*:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'
	@echo -e "$(COLOR_BOLD)App$(COLOR_RESET)"
	@grep -E '^app-[a-zA-Z_-]*:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'
	@echo -e "$(COLOR_BOLD)Quality and info$(COLOR_RESET)"
	@grep -E '^(lint|preflight|clean|status)[a-zA-Z_-]*:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'
	@echo ""
	@echo "Overrides: TALKS_DIR=$(TALKS_DIR)"
	@echo "           VOTING_URL=$(VOTING_URL)  APP_PORT=$(APP_PORT)"

# ==============================================================================
# Guards
# ==============================================================================

.PHONY: preflight guard-talk guard-talks-dir guard-venv

preflight: guard-talk guard-talks-dir ## Check talk CLI and talks checkout

guard-talk:
	@[ -n "$(TALK)" ] || { echo "ERROR: talk CLI not found. Install: cd ~/Repos/own/oehrlis/ai-toolkit && make install-cli" >&2; exit 1; }

guard-talks-dir:
	@[ -f "$(TALKS_DIR)/talks/$(TALK_SLUG)/talk.yaml" ] || \
	  { echo "ERROR: no talks/$(TALK_SLUG)/talk.yaml below TALKS_DIR=$(TALKS_DIR) - set TALKS_DIR to the talks checkout" >&2; exit 1; }
	@grep -q 'hold-my-beer/slides' "$(TALKS_DIR)/talks/$(TALK_SLUG)/talk.yaml" || \
	  { echo "ERROR: $(TALKS_DIR)/talks/$(TALK_SLUG)/talk.yaml does not use the hold-my-beer slide sources (old recipe?)." >&2; \
	    echo "       Use the checkout with branch talk/wissen-nicht, e.g. TALKS_DIR=$(abspath $(CURDIR)/../talks-dinu)" >&2; exit 1; }

guard-venv:
	@[ -x "$(PYTHON)" ] || { echo "ERROR: $(VENV) missing - run: make app-venv" >&2; exit 1; }

# ==============================================================================
# Deck
# ==============================================================================

.PHONY: deck deck-private deck-pdf deck-dry-run

deck: preflight ## Build the public deck (drawings only) into the repo
	$(Q)$(BUILD)

deck-private: preflight ## Build the deck with private photos to OneDrive (PRIVATE_OUT, outside the repo)
	@[ -d "$(HMB_PRIVATE_DIR)" ] || { echo "ERROR: HMB_PRIVATE_DIR not found: $(HMB_PRIVATE_DIR)" >&2; exit 1; }
	$(Q)mkdir -p "$(dir $(PRIVATE_OUT))"
	$(Q)HMB_PRIVATE_DIR="$(HMB_PRIVATE_DIR)" $(BUILD) -o "$(PRIVATE_OUT)"
	@echo "OK: private deck $(PRIVATE_OUT)"

deck-pdf: preflight ## Build the public deck as PDF (slides/$(EVENT)/$(TALK_SLUG).pdf)
	$(Q)$(BUILD) --pdf

deck-dry-run: preflight ## Generate atoms and list the slide plan, write no deck
	$(Q)$(BUILD) --dry-run

# ==============================================================================
# App
# ==============================================================================

.PHONY: app-venv app-test app-run app-stop app-status

app-venv: ## Create the app venv and install locked dependencies
	$(Q)[ -x "$(PYTHON)" ] || python3 -m venv "$(VENV)"
	$(Q)"$(PYTHON)" -m pip install -q -r "$(APP_DIR)/requirements.lock" -r "$(APP_DIR)/requirements-dev.txt"
	@echo "OK: $(VENV) ready"

app-test: guard-venv ## Run the app test suite (pytest)
	$(Q)cd "$(APP_DIR)" && .venv/bin/python -m pytest -q

app-run: ## Start the app locally (APP_PORT, default 5000; dev admin password oracle-dev)
	$(Q)cd "$(APP_DIR)" && PORT="$(APP_PORT)" ./start.sh

app-stop: ## Stop the locally started app
	$(Q)cd "$(APP_DIR)" && ./stop.sh

app-status: ## Show process and readiness of the local app
	$(Q)cd "$(APP_DIR)" && PORT="$(APP_PORT)" ./status.sh

# ==============================================================================
# Quality
# ==============================================================================

.PHONY: lint lint-markdown lint-shell lint-python

lint: lint-markdown lint-shell lint-python ## Run all linters

lint-markdown: ## markdownlint on repo docs (app/README.md is Martin's, not gated)
	@[ -n "$(MARKDOWNLINT)" ] || { echo "WARN: markdownlint not found - skipped (npm i -g markdownlint-cli)"; exit 0; }
	$(Q)$(MARKDOWNLINT) README.md docs/*.md pool/*.md $(SLIDES_DIR)/*.md
	@echo "OK: markdownlint"

lint-shell: ## shellcheck on slide and app scripts
	@[ -n "$(SHELLCHECK)" ] || { echo "WARN: shellcheck not found - skipped (brew install shellcheck)"; exit 0; }
	$(Q)$(SHELLCHECK) "$(SLIDES_DIR)/build.sh"
	$(Q)$(SHELLCHECK) -S warning $(APP_DIR)/*.sh $(APP_DIR)/deploy/*.sh $(APP_DIR)/tools/*.sh
	@echo "OK: shellcheck"

lint-python: ## Syntax check of the slide generators
	$(Q)python3 -m py_compile "$(SLIDES_DIR)/generate.py" "$(SLIDES_DIR)/img/brain.py" "$(SLIDES_DIR)/img/gen_phone.py"
	@echo "OK: py_compile"

# ==============================================================================
# Cleanup and info
# ==============================================================================

.PHONY: clean status

clean: ## Remove generated atoms and Python caches (keeps the built deck and the venv)
	$(Q)rm -rf "$(SLIDES_DIR)/build" "$(SLIDES_DIR)/__pycache__" "$(SLIDES_DIR)/img/__pycache__"
	@echo "OK: clean"

status: ## Show branch, working tree and deck build info
	@echo "Branch: $$($(GIT) rev-parse --abbrev-ref HEAD)"
	@$(GIT) status --short
	@ls -la "$(SLIDES_DIR)/$(EVENT)/" 2>/dev/null || true
	@echo "TALKS_DIR: $(TALKS_DIR)"
