# Data Ingestor is a CLI tool (the Chunk stage of the Foundry pipeline), not a
# long-running service. The image runs the CLI; see docker-compose.yml.
#
# Dependencies come from poetry.lock (hash-verified). Regenerate the lock with
# `poetry lock` after changing pyproject.toml, or the build fails at the export step.

FROM python:3.11-slim AS builder

# Build tools for any dependency that has no wheel for this platform
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Poetry is only used to export the locked requirements; it is not copied to the final image
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir "poetry==2.1.1" "poetry-plugin-export>=1.9,<2"

WORKDIR /build
COPY pyproject.toml poetry.lock ./
RUN poetry export --only main --format requirements.txt --output requirements.txt

# Install into a virtual environment with hash verification
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

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

COPY --chown=ingestor:ingestor src/ ./src/

USER ingestor

ENV PYTHONPATH=/app/src \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# No ports and no health check: this is a command-line tool
ENTRYPOINT ["python", "-m", "data_ingestor.cli.main"]
CMD ["--help"]
