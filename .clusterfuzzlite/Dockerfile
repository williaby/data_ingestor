# SPDX-FileCopyrightText: 2026 Byron Williams
# SPDX-License-Identifier: MIT
#
# Build image for ClusterFuzzLite (.github/workflows/cifuzzy.yml). The action
# builds this file from the repository root, then runs build.sh inside it to
# compile the Atheris harnesses in fuzz/. The base image provides Python 3.11,
# which Atheris requires (it does not support 3.12 or later).
FROM gcr.io/oss-fuzz-base/base-builder-python@sha256:21f6fab17ace4dc76e1c56de91ee95d3d03da021df94b41056ba036f6c6f55e9

# The build runs as root because the action mounts host directories at /out and
# /work and the OSS-Fuzz compile step installs packages system-wide; this image
# is used only for the CI fuzz build and is never deployed.
WORKDIR $SRC/data_ingestor
COPY pyproject.toml README.md ./
COPY src ./src
COPY fuzz ./fuzz
COPY .clusterfuzzlite/build.sh $SRC/
