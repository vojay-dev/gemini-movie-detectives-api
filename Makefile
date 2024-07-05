define MOVIE_DETECTIVES_LOGO
   __  __            _        ____       _            _   _
  |  \/  | _____   _(_) ___  |  _ \  ___| |_ ___  ___| |_(_)_   _____  ___
  | |\/| |/ _ \ \ / / |/ _ \ | | | |/ _ \ __/ _ \/ __| __| \ \ / / _ \/ __|
  | |  | | (_) \ V /| |  __/ | |_| |  __/ ||  __/ (__| |_| |\ V /  __/\__ |
  |_|  |_|\___/ \_/ |_|\___| |____/ \___|\__\___|\___|\__|_| \_/ \___||___/
endef
export MOVIE_DETECTIVES_LOGO

.PHONY: all
all:
	@echo "$$MOVIE_DETECTIVES_LOGO"
	@echo "Run make help to see available commands"

.PHONY: help
help:
	@echo "$$MOVIE_DETECTIVES_LOGO"
	@echo "Available commands:"
	@echo "  make .venv          - Install dependencies using Poetry"
	@echo "  make run            - Run service locally"
	@echo "  make test           - Run tests"
	@echo "  make ruff           - Run linter"
	@echo "  make check          - Run tests and linter"
	@echo "  make docker-build   - Build Docker image"
	@echo "  make docker-start   - Start Docker container"
	@echo "  make docker-stop    - Stop Docker container"
	@echo "  make docker-logs    - View Docker container logs"
	@echo "  make clean          - Remove build artifact"
	@echo "  make build          - Build deployable artifact"

# Install dependencies
.venv:
	@command -v poetry >/dev/null 2>&1 || { echo >&2 "Poetry is not installed"; exit 1; }
	poetry config virtualenvs.in-project true --local
	poetry install
	@echo "Virtual env was created within project dir as .venv"

# Run service locally
.PHONY: run
run:
	poetry run fastapi dev gemini_movie_detectives_api/main.py

# Run tests and linter
.PHONY: test
test:
	poetry run python -m pytest tests/ -v -Wignore

.PHONY: ruff
ruff:
	poetry run ruff check --fix

.PHONY: check
check: test ruff

# Docker interaction to build image and run service with Docker
.PHONY: docker-build
docker-build:
	docker build -t gemini-movie-detectives-api .

.PHONY: docker-start
docker-start: docker-build
	docker run -d --rm --name gemini-movie-detectives-api -p 9091:9091 gemini-movie-detectives-api
	@echo "Gemini Movie Detectives Backend running on port 9091"

.PHONY: docker-stop
docker-stop:
	@if [ $$(docker ps -q -f name=gemini-movie-detectives-api) ]; then \
		echo "Stopping gemini-movie-detectives-api container..."; \
		docker stop gemini-movie-detectives-api; \
	else \
		echo "Container gemini-movie-detectives-api is not running"; \
	fi

.PHONY: docker-logs
docker-logs:
	@if [ $$(docker ps -q -f name=gemini-movie-detectives-api) ]; then \
		docker logs -f gemini-movie-detectives-api; \
	else \
		echo "Container gemini-movie-detectives-api is not running"; \
	fi

# Remove existing build artifact
.PHONY: clean
clean:
	rm -rf gemini-movie-detectives-api_latest.tar.gz

# Build a deployable artifact
.PHONY: build
build: clean
	docker image rm gemini-movie-detectives-api
	docker build -t gemini-movie-detectives-api .
	docker save gemini-movie-detectives-api:latest | gzip > gemini-movie-detectives-api_latest.tar.gz
