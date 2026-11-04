# Етап 1: Збірка залежностей через uv
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN uv sync --frozen --no-dev

# Етап 2: Фінальний легкий образ
FROM python:3.11-slim-bookworm
WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/pyproject.toml ./

# Створюємо не-root користувача для безпеки
RUN useradd -u 1000 findex && chown -R findex:findex /app
USER findex

ENV PATH="/app/.venv/bin:$PATH"
ENV INDEX_PATH="index.bin"

EXPOSE 8000
CMD ["uvicorn", "findex.web.app:app", "--host", "0.0.0.0", "--port", "8000"]