FROM --platform=linux/amd64 python:3.12

WORKDIR /workdir
COPY ./pyproject.toml /workdir/pyproject.toml
RUN pip3 install poetry
RUN poetry config virtualenvs.create false
RUN poetry install

COPY . /workdir
EXPOSE 9091
CMD ["uvicorn", "gemini_movie_detectives_api.main:app", "--host", "0.0.0.0", "--port", "9091"]
