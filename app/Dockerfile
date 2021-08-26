FROM python:3.8.11-slim-buster

WORKDIR /app
COPY ./ /app/

RUN pip install pipenv && pipenv install

ENTRYPOINT [ "pipenv", "run", "python", "main.py" ]
