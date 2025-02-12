FROM python:3.13.2-slim-bookworm

WORKDIR /app

COPY requirements.txt .
COPY run.sh .
COPY ./src/main.py ./src/
COPY ./src/wsgi.py ./src/
COPY 01_internal.sh .
RUN ./01_internal.sh
RUN rm -rf ./01_internal.sh
