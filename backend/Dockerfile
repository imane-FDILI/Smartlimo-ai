FROM python:3.11-slim

WORKDIR /app

COPY requirements-api.txt .

RUN pip install --no-cache-dir -r requirements-api.txt

COPY app ./app
COPY datasets ./datasets
COPY data ./data

EXPOSE 8000

# Shell form (not exec/JSON form) so that ${PORT} is expanded by the shell;
# Railway/Render/Heroku-style platforms inject PORT and route traffic there,
# defaulting to 8000 for local `docker run` without -e PORT=...
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}