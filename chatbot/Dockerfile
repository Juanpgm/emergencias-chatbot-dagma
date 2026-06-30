FROM python:3.11-slim

WORKDIR /app

COPY chatbot/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ ./shared/
COPY chatbot/ ./chatbot/

ENV PYTHONPATH=/app
ENV PORT=8081

EXPOSE 8081

CMD uvicorn chatbot.app.main:app --host 0.0.0.0 --port $PORT
