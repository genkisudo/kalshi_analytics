FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.8.5 \
    POETRY_VIRTUALENVS_CREATE=false

RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-interaction --no-ansi --only main --no-root

COPY extract_chess.py ./

# Cloud Run Job uses the runtime service account for BigQuery (no ADC file).
CMD ["python", "extract_chess.py", "--load"]
