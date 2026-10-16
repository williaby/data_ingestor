# SPDX-FileCopyrightText: 2026 Byron Williams
# SPDX-License-Identifier: MIT
#
# Chunk-job image: the data-ingestor CLI (the Chunk stage of the Foundry
# pipeline). It converts a document with docling-serve, chunks it, and writes
# one RAGChunkSet.json per document to the mounted /data/chunks directory. It
# is a run-to-completion job, not a service: no port, no health check, and
# no embedding, vector store, or model key (the consuming application owns
# those).
#
# Hardened Debian-based Python images (the -dev variant has a shell and apt;
# the runtime variant is distroless) so the virtualenv's interpreter path is
# identical in both stages. Dependencies come from uv.lock, runtime group
# only. The image holds no secrets: every setting is read from
# DATA_INGESTOR_* environment variables at start.
#
# #CRITICAL: the build needs tiktoken, numpy, scipy and psutil in the runtime
# dependency list, which williaby/data_ingestor PR #76 declares. Without it
# the CLI fails at import. #VERIFY: `data-ingestor chunk --help` runs in the
# smoke test of .github/workflows/build-chunk-image.yml.

# =============================================================================
# Stage 1: builder
# =============================================================================
# Source: dhi.io/python:3.12-debian13-dev -> ghcr.io/byronwilliamscpa/dhi-python:3.12-debian13-dev
FROM ghcr.io/byronwilliamscpa/dhi-python@sha256:fe90645fdf287796e54df8b16360094e0001c607f7105ce3c15f026a6bcf2a3b AS builder

WORKDIR /app

# libmagic is a runtime dependency of python-magic, which the package imports
# at load time. The distroless runtime stage has no package manager, so the
# shared library and its compiled database are copied out of this stage.
# The builder stage is discarded, so apt version pinning is omitted (DL3008).
# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends libmagic1t64 libmagic-mgc \
    && apt-get clean

COPY --from=ghcr.io/astral-sh/uv:0.8.17@sha256:e4644cb5bd56fdc2c5ea3ee0525d9d21eed1603bccd6a21f887a938be7e85be1 /uv /usr/local/bin/uv

# Runtime dependencies only: no dev, test, docs, ml or azure groups and no
# optional extras (no torch, CUDA, Marker, or the full docling package).
# Conversion goes through docling-serve over HTTP.
#
# Nothing here runs package build scripts: --no-build makes uv refuse any
# source distribution, so every dependency is installed from a prebuilt wheel
# and no setup.py executes during the image build. langdetect is the one locked
# dependency that ships only as a source distribution, so it is left out
# (--no-install-package). It is an optional import in the PDF parser, which
# skips language detection when it is missing, and the chunk job does not use
# that parser.
ENV UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-default-groups --no-install-project \
        --no-build --no-install-package langdetect

# The project itself is built into a wheel by its own build backend (hatchling,
# our code only) and installed from that wheel with --no-build. The wheel
# directory stays in this stage, which is discarded. Settings creates
# storage_path (./data/processed) when it loads, and every CLI command loads
# it, so pre-create it for a read-only root filesystem.
COPY src ./src
RUN uv build --wheel --out-dir /tmp/dist \
    && uv pip install --python /app/.venv/bin/python --no-build --no-deps /tmp/dist/*.whl \
    && mkdir -p /app/data/processed /app/output

# =============================================================================
# Stage 2: runtime (distroless, no shell)
# =============================================================================
# Source: dhi.io/python:3.12-debian13 -> ghcr.io/byronwilliamscpa/dhi-python:3.12-debian13
FROM ghcr.io/byronwilliamscpa/dhi-python@sha256:a5425367554af74a6894e94ed3e98fee761973235307fc92438850163bf5f200

LABEL org.opencontainers.image.title="Data Ingestor chunk job"
LABEL org.opencontainers.image.description="Converts documents with docling-serve and writes RAGChunkSet.json chunk sets"
LABEL org.opencontainers.image.source="https://github.com/williaby/data_ingestor"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

COPY --from=builder /usr/lib/x86_64-linux-gnu/libmagic.so.1* /usr/lib/x86_64-linux-gnu/
COPY --from=builder /usr/lib/file/magic.mgc /usr/lib/file/magic.mgc
COPY --from=builder --chown=65532:65532 /app/.venv /app/.venv
COPY --from=builder --chown=65532:65532 /app/data /app/data
COPY --from=builder --chown=65532:65532 /app/output /app/output

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MAGIC=/usr/lib/file/magic.mgc \
    PATH="/app/.venv/bin:$PATH"

# Non-root. The /data/chunks volume must be writable by this UID on the host
# (the consuming application mounts the same directory read-only).
# #ASSUME: the home server can reach the Hugging Face hub for the chunk
# tokenizer (DATA_INGESTOR_CHUNK_TOKENIZER) on first use, or mounts a
# pre-populated HF_HOME. #VERIFY: run one `chunk` job on the home server and
# confirm the tokenizer loads; pin DATA_INGESTOR_CHUNK_TOKENIZER_REVISION.
USER 65532:65532

# No ports and no health check: this is a command-line job.
ENTRYPOINT ["data-ingestor"]
CMD ["--help"]
