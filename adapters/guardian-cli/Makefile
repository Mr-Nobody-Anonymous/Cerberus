# Makefile for Guardian CLI
# Automation of common development and deployment tasks

# -----------------------------------------------------------------------------
# Variables
# -----------------------------------------------------------------------------
VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(PYTHON) -m pip
DOCKER := docker
DOCKER_COMPOSE := docker-compose
APP_NAME := guardian-cli
IMAGE_NAME := guardian-cli
VERSION := $(shell grep "version =" pyproject.toml | head -n 1 | cut -d '"' -f 2)

# Colors for help message
CYAN := \033[36m
RESET := \033[0m

# -----------------------------------------------------------------------------
# Default target
# -----------------------------------------------------------------------------
.DEFAULT_GOAL := help

# -----------------------------------------------------------------------------
# Help
# -----------------------------------------------------------------------------
.PHONY: help
help: ## Display this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(CYAN)%-20s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# -----------------------------------------------------------------------------
# Development
# -----------------------------------------------------------------------------
.PHONY: venv
venv: ## Create virtual environment
	test -d $(VENV) || python3 -m venv $(VENV)

.PHONY: setup
setup: venv ## Initialize development environment (.env, venv, directories)
	test -f .env || cp .env.example .env
	mkdir -p reports logs
	# @echo " Environment initialized. Please edit .env with your API keys."

.PHONY: install
# -----------------------------------------------------------------------------
.PHONY: install
install: venv ## Install dependencies for development
	$(PIP) install -e ".[dev]"

.PHONY: update
update: ## Update dependencies
	$(PIP) install --upgrade -e ".[dev]"

.PHONY: clean
clean: ## Clean up build artifacts and cache
	rm -rf build/ dist/ *.egg-info .pytest_cache .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# -----------------------------------------------------------------------------
# Quality Assurance
# -----------------------------------------------------------------------------
.PHONY: lint
lint: ## Run linting (ruff & black check)
	ruff check .
	black --check .

.PHONY: format
format: ## Format code (black & ruff fix)
	black .
	ruff check --fix .

.PHONY: test
test: ## Run tests
	pytest

# -----------------------------------------------------------------------------
# Docker
# -----------------------------------------------------------------------------
.PHONY: docker-build
docker-build: ## Build the Docker image
	$(DOCKER) build -t $(IMAGE_NAME):latest -t $(IMAGE_NAME):$(VERSION) .

.PHONY: docker-run
docker-run: ## Run the Docker container
	$(DOCKER) run --rm -it $(IMAGE_NAME):latest

.PHONY: compose-up
compose-up: ## Start services with Docker Compose
	$(DOCKER_COMPOSE) up -d

.PHONY: compose-down
compose-down: ## Stop services with Docker Compose
	$(DOCKER_COMPOSE) down

.PHONY: compose-logs
compose-logs: ## View logs from Docker Compose services
	$(DOCKER_COMPOSE) logs -f

# -----------------------------------------------------------------------------
# CLI Execution
# -----------------------------------------------------------------------------
.PHONY: run
run: ## Run the CLI tool (usage: make run ARGS="scan --target example.com")
	$(PYTHON) -m cli.main $(ARGS)

