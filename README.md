# Gemini Movie Detectives API

## Basic project setup
```sh
poetry config virtualenvs.in-project true
poetry new gemini-movie-detectives-api
cd gemini-movie-detectives-api
poetry add 'uvicorn[standard]'
poetry add fastapi

poetry add pydantic-settings
poetry add httpx
poetry add 'google-cloud-aiplatform>=1.38'
poetry add jinja2
```

`gemini_movie_detectives/main.py`:
```py
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}
```

Run:
```sh
source .venv/bin/activate
uvicorn gemini_movie_detectives_api.main:app --reload
curl -s localhost:8000/ | jq .
```
