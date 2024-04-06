all:
	@echo "see README.md"

.PHONY: run
run:
	uvicorn gemini_movie_detectives_api.main:app --reload

.PHONY: clean
clean:
	rm -rf gemini-movie-detectives-api_latest.tar.gz

.PHONY: build
build: clean
	docker image rm gemini-movie-detectives-api
	docker build -t gemini-movie-detectives-api .
	docker save gemini-movie-detectives-api:latest | gzip > gemini-movie-detectives-api_latest.tar.gz
