all:
	@echo "see README.md"

# Install dependencies
.venv:
	poetry install

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
	docker stop gemini-movie-detectives-api

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
