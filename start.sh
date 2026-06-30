#!/bin/sh
set -e
export PYTHONPATH=/app
if [ "$SERVICE_TYPE" = "admin" ]; then
  exec uvicorn admin.app.main:app --host 0.0.0.0 --port "${PORT:-8082}"
else
  exec uvicorn chatbot.app.main:app --host 0.0.0.0 --port "${PORT:-8081}"
fi
