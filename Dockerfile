# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.11.4
FROM python:${PYTHON_VERSION}-slim as base

# не писать pyc
ENV PYTHONDONTWRITEBYTECODE=1

# не буфферизировать вывод
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# запускать из-под непривилигерованного пользователя
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

# использовать кэш для сборки /root/.cache/pip
# подключить файл с зависимостями
# Leverage a cache mount to /root/.cache/pip to speed up subsequent builds.
# Leverage a bind mount to requirements.txt to avoid having to copy them into
# into this layer.
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    python3 -m pip install -r requirements.txt

# Switch to the non-privileged user to run the application.
USER appuser

# Copy the source code into the container.
COPY . .

# Expose the port that the application listens on.
EXPOSE 3000

# Run the application.
CMD python3 -m flask run --host=0.0.0.0 --port=3000