#!/bin/sh

set -xe

python src/main.py
gunicorn --bind 0.0.0.0:8000 --chdir ./src/ wsgi:application
