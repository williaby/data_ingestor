# Data Ingestor is a CLI tool (the Chunk stage of the Foundry pipeline), not a
# long-running service. The image runs the CLI; see docker-compose.yml.
#
# Dependencies come from uv.lock (hash-verified). Run `uv lock` after changing
# pyproject.toml, or `uv sync --frozen` fails the build.

FROM python:3.11-slim AS builder

# Build tools for any dependency that has no wheel for this platform
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# uv is only used to build the environment; it is not copied to the final image
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv

WORKDIR /build
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=0 \
    UV_LINK_MODE=copy

# Runtime dependencies only: no dev, test, docs, ml or azure groups, no optional extras
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-default-groups --no-install-project

# Install the project itself
COPY src/ ./src/
RUN uv sync --frozen --no-default-groups --no-editable

# Minimal final image
FROM python:3.11-slim

# libmagic is required by python-magic (format detection)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Non-root user
RUN groupadd -r ingestor && \
    useradd -r -g ingestor -u 1000 -m -s /bin/bash ingestor

WORKDIR /app
RUN mkdir -p /app/data /app/output && chown -R ingestor:ingestor /app

USER ingestor

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random

# No ports and no health check: this is a command-line tool
ENTRYPOINT ["data-ingestor"]
CMD ["--help"]
