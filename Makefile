all:
	@echo "see README.md"

.PHONY: run
run:
	uvicorn gemini_movie_detectives_api.main:app --reload
