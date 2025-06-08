#!/bin/bash
gunicorn --bind=0.0.0.0:8000 --workers=4 --timeout 300 --chdir /home/site/wwwroot app:app
