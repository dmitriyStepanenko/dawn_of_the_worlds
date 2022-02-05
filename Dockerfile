###############################################
# Base Image
###############################################
FROM python:3.9-slim as base

ENV PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1

WORKDIR /app

###############################################
# Builder Image
###############################################
FROM base as builder

ENV PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.0.5

COPY pyproject.toml poetry.lock ./
RUN pip install "poetry==$POETRY_VERSION" \
    && poetry config virtualenvs.in-project true \
    && poetry install --no-dev

FROM base AS prod

COPY --from=builder app/.venv /venv

WORKDIR /app
COPY /app /app/app

ENV PYTHONPATH=${PYTHONPATH}:${PWD}

CMD ["/venv/bin/python", "app/telegram_bot/run_bot.py"]