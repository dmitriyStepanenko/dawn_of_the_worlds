FROM python:3.9

RUN mkdir /app

COPY /app /app/app
COPY pyproject.toml /app

WORKDIR /app

ENV PYTHONPATH=${PYTHONPATH}:${PWD}

RUN pip3 install poetry
RUN poetry config virtualenvs.create false
RUN poetry install --no-dev

CMD ["python", "app/telegram_bot/run_bot.py"]