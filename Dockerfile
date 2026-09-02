FROM python:3.14-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VERSION=2.1.1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1
RUN pip install --no-cache-dir poetry==$POETRY_VERSION
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry install --with dev
ENV PATH="/app/.venv/bin:$PATH"
RUN useradd --create-home appuser
COPY --chown=appuser . /app
RUN flake8
USER appuser