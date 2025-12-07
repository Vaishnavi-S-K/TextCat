#!/bin/sh
# Railway startup script - handles dynamic PORT
PORT=${PORT:-5000}
exec gunicorn --bind 0.0.0.0:$PORT --workers 4 --threads 2 --timeout 60 --access-logfile - --error-logfile - app:app
