# Gemini Movie Detectives API

This project uses:

* Python 3.12 + FastAPI
* Poetry for dependency management
* Docker for deployment
* TMDB API for movie data
* VertexAI and Gemini for generating movie quizzes

## Project setup

**(Optional) Configure poetry to use in-project virtualenvs**:
```sh
poetry config virtualenvs.in-project true
```

**Install dependencies**:
```sh
poetry install
```

**Run**:
```sh
source .venv/bin/activate
uvicorn gemini_movie_detectives_api.main:app --reload
curl -s localhost:8000/ | jq .
```

## Configuration

The API is configured via environment variables. If a `.env` file is present in the project root, it will be loaded
automatically. The following variables must be set:

* `TMDB_API_KEY`: The API key for The Movie Database (TMDB).
* `GCP_PROJECT_ID`: The ID of the Google Cloud Platform (GCP) project used for VertexAI and Gemini.
* `GCP_LOCATION`: The location used for prediction processes.
* `GCP_SERVICE_ACCOUNT_FILE`: The path to the service account file used for authentication with GCP.

There are more config variables with defaults, which can be used to adjust the default API behavior.

## Docker

**Build**:
```sh
docker image rm gemini-movie-detectives-api
docker build -t gemini-movie-detectives-api .
```

**Run**:
```sh
docker run -d --rm --name gemini-movie-detectives-api -p 9091:9091 gemini-movie-detectives-api
curl -s localhost:9091/movies | jq .
docker stop gemini-movie-detectives-api
```

**Save image for deployment**:
```sh
docker save gemini-movie-detectives-api:latest | gzip > gemini-movie-detectives-api_latest.tar.gz
```
