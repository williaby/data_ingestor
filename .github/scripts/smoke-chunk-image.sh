#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Byron Williams
# SPDX-License-Identifier: MIT
#
# Smoke test for the chunk-job image. One script, called by both jobs of the
# Build Chunk Image workflow: the build job runs it on the freshly built local
# image, the push job runs it again on the image it pulled back from the
# registry by digest, so the bytes that get signed and tagged are the bytes
# that were tested.
#
# Usage: smoke-chunk-image.sh IMAGE_REFERENCE
#
# The job is a CLI, so the test checks what a broken build would lose: the
# image runs as a non-root user, the entrypoint starts with a read-only root
# filesystem, the whole dependency closure of the chunk command imports
# (docling-core, transformers, tiktoken, libmagic), and the libmagic database
# is found and answers. `--help` imports nothing heavy (the chunk command
# imports its dependencies when it runs), so the import check is separate.
# No document or service is needed.
set -euo pipefail

if [[ "$#" -ne 1 || -z "$1" ]]; then
  echo "usage: $0 IMAGE_REFERENCE" >&2
  exit 2
fi
IMG="$1"

user="$(docker inspect --format '{{.Config.User}}' "${IMG}")"
if [[ "${user}" != "65532:65532" ]]; then
  echo "expected user 65532:65532, got '${user}'"
  exit 1
fi

docker run --rm --read-only --tmpfs /tmp "${IMG}" --help
docker run --rm --read-only --tmpfs /tmp "${IMG}" chunk --help

# from_buffer with mime=True loads the compiled libmagic database from the
# MAGIC path, so a missing or unreadable magic.mgc fails here, not in production.
docker run --rm --read-only --tmpfs /tmp --entrypoint python "${IMG}" -c '
import magic, tiktoken, transformers
import data_ingestor.cli.main
from data_ingestor.chunking import HybridDocumentChunker
from data_ingestor.conversion import DoclingServeClient, docling_json_to_document
from data_ingestor.export import build_chunk_set, write_chunk_set

detected = magic.from_buffer(b"%PDF-1.4", mime=True)
if detected != "application/pdf":
    raise SystemExit(f"libmagic detected {detected!r}, expected application/pdf")
print("imports ok")
'
