#!/bin/bash

# Install requirements
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput
