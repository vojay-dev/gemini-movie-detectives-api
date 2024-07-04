all:
	@echo "see README.md"

.venv:
	poetry install

.PHONY: run
run:
	poetry run fastapi dev gemini_movie_detectives_api/main.py

.PHONY: test
test:
	poetry run python -m pytest tests/ -v -Wignore

.PHONY: ruff
ruff:
	poetry run ruff check --fix

.PHONY: clean
clean:
	rm -rf gemini-movie-detectives-api_latest.tar.gz

.PHONY: build
build: clean
	docker image rm gemini-movie-detectives-api
	docker build -t gemini-movie-detectives-api .
	docker save gemini-movie-detectives-api:latest | gzip > gemini-movie-detectives-api_latest.tar.gz
