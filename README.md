# Gemini Movie Detectives API

Frontend: [gemini-movie-detectives-ui](https://github.com/vojay-dev/gemini-movie-detectives-ui)

![logo](doc/logo.png)
Try it yourself: [movie-detectives.com](https://movie-detectives.com/)

- [Project overview](#project-overview)
- [Project setup](#project-setup)
- [Configuration](#configuration)
- [Docker](#docker)
  - [Build](#build)
  - [Run](#run)
  - [Save image for deployment](#save-image-for-deployment)
- [API Example Usage](#api-example-usage)
  - [Get a list of movies](#get-a-list-of-movies)
  - [Get a customized list of movies](#get-a-customized-list-of-movies)
  - [Get a random movie with more details](#get-a-random-movie-with-more-details)
  - [Start a quiz](#start-a-quiz)
  - [Send answer and finish a quiz](#send-answer-and-finish-a-quiz)

## Project overview

- Python 3.12 + FastAPI
- Poetry for dependency management
- Docker for deployment
- TMDB API for movie data
- VertexAI and Gemini for generating movie quizzes

![system overview](doc/system-overview.png)
*Movie Detectives - System Overview*

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
curl -s localhost:8000/movies | jq .
```

## Configuration

The API is configured via environment variables. If a `.env` file is present in the project root, it will be loaded
automatically. The following variables must be set:

- `TMDB_API_KEY`: The API key for The Movie Database (TMDB).
- `GCP_PROJECT_ID`: The ID of the Google Cloud Platform (GCP) project used for VertexAI and Gemini.
- `GCP_LOCATION`: The location used for prediction processes.
- `GCP_SERVICE_ACCOUNT_FILE`: The path to the service account file used for authentication with GCP.

There are more config variables with defaults, which can be used to adjust the default API behavior.

## Docker

### Build

```sh
docker image rm gemini-movie-detectives-api
docker build -t gemini-movie-detectives-api .
```

### Run

```sh
docker run -d --rm --name gemini-movie-detectives-api -p 9091:9091 gemini-movie-detectives-api
curl -s localhost:9091/movies | jq .
docker stop gemini-movie-detectives-api
```

### Save image for deployment

```sh
docker save gemini-movie-detectives-api:latest | gzip > gemini-movie-detectives-api_latest.tar.gz
```

## API Example Usage

### Get a list of movies

```sh
curl -s localhost:8000/movies | jq .
```

### Get a customized list of movies

```sh
curl -s "localhost:8000/movies?page=3&vote-avg-min=8&vote-count-min=1000" | jq ".[0]"
```

```json
{
  "adult": false,
  "backdrop_path": "/eHMh7kChaNeD4VTdMCXLJbRTzcI.jpg",
  "genre_ids": [
    18,
    36,
    10752
  ],
  "id": 753342,
  "original_language": "en",
  "original_title": "Napoleon",
  "overview": "An epic that details the checkered rise and fall of French Emperor Napoleon Bonaparte and his relentless journey to power through the prism of his addictive, volatile relationship with his wife, Josephine.",
  "popularity": 193.344,
  "poster_path": "/vcZWJGvB5xydWuUO1vaTLI82tGi.jpg",
  "release_date": "2023-11-22",
  "title": "Napoleon",
  "video": false,
  "vote_average": 6.484,
  "vote_count": 1953,
  "poster_url": "https://image.tmdb.org/t/p/original/vcZWJGvB5xydWuUO1vaTLI82tGi.jpg"
}
```

## Get a random movie with more details

```sh
curl -s localhost:8000/movies/random | jq .
```

```json
{
  "adult": false,
  "backdrop_path": "/oe7mWkvYhK4PLRNAVSvonzyUXNy.jpg",
  "belongs_to_collection": null,
  "budget": 85000000,
  "genres": [
    {
      "id": 28,
      "name": "Action"
    },
    {
      "id": 53,
      "name": "Thriller"
    }
  ],
  "homepage": "https://www.amazon.com/gp/video/detail/B0CH5YQPZQ",
  "id": 359410,
  "imdb_id": "tt3359350",
  "original_language": "en",
  "original_title": "Road House",
  "overview": "Ex-UFC fighter Dalton takes a job as a bouncer at a Florida Keys roadhouse, only to discover that this paradise is not all it seems.",
  "popularity": 1880.547,
  "poster_path": "/bXi6IQiQDHD00JFio5ZSZOeRSBh.jpg",
  "production_companies": [
    {
      "id": 21,
      "logo_path": "/usUnaYV6hQnlVAXP6r4HwrlLFPG.png",
      "name": "Metro-Goldwyn-Mayer",
      "origin_country": "US"
    },
    {
      "id": 1885,
      "logo_path": "/xlvoOZr4s1PygosrwZyolIFe5xs.png",
      "name": "Silver Pictures",
      "origin_country": "US"
    }
  ],
  "production_countries": [
    {
      "iso_3166_1": "US",
      "name": "United States of America"
    }
  ],
  "release_date": "2024-03-08",
  "revenue": 0,
  "runtime": 121,
  "spoken_languages": [
    {
      "english_name": "English",
      "iso_639_1": "en",
      "name": "English"
    }
  ],
  "status": "Released",
  "tagline": "Take it outside.",
  "title": "Road House",
  "video": false,
  "vote_average": 7.14,
  "vote_count": 1182,
  "poster_url": "https://image.tmdb.org/t/p/original/bXi6IQiQDHD00JFio5ZSZOeRSBh.jpg"
}
```

### Start a quiz

```sh
curl -s -X POST localhost:8000/quiz \
  -H 'Content-Type: application/json' \
  -d '{"vote_avg_min": 5.0, "vote_count_min": 1000.0, "popularity": 3}' | jq .
```

```json
{
  "quiz_id": "84c19425-c179-4198-9773-a8a1b71c9605",
  "question": {
    "question": "Imagine a family road trip, but not just any road trip, a life-or-death race against time! A giant space rock is hurtling towards Earth, and this family is trying to outrun the end of the world. Along the way, they witness cities crumbling like sandcastles and meet people who are both kind and cruel. Can they make it to safety in time?",
    "hint1": "The movie is all about a family trying to survive a global catastrophe.",
    "hint2": "Gr_e_l_nd"
  },
  "movie": {...}
}
```

### Send answer and finish a quiz

```sh
curl -s -X POST localhost:8000/quiz/84c19425-c179-4198-9773-a8a1b71c9605/answer \
  -H 'Content-Type: application/json' \
  -d '{"answer": "Greenland"}' | jq .
```

```json
{
  "quiz_id": "84c19425-c179-4198-9773-a8a1b71c9605",
  "question": {...},
  "movie": {...},
  "user_answer": "Greenland",
  "result": {
    "points": "3",
    "answer": "Congratulations! You got it! Greenland is the movie we were looking for. You're like a human GPS, always finding the right way!"
  }
}
```
