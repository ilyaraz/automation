#!/bin/sh

set -xe

python main.py
gunicorn --bind 0.0.0.0:8000 wsgi:application
