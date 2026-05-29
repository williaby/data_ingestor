#!/bin/bash -eu
# ClusterFuzzLite build script for Data Ingestor
# Uses OSS-Fuzz compile_python_fuzzer to create proper fuzz target executables

echo "=== ClusterFuzzLite Build Debug ==="
echo "SRC: $SRC"
echo "OUT: $OUT"
echo "WORK: $WORK"
echo "===================================="

# Verify Python version compatibility with Atheris (3.8-3.11)
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')

echo "Python version: $PYTHON_VERSION"

if [ "$PYTHON_MAJOR" -ne 3 ] || [ "$PYTHON_MINOR" -lt 8 ] || [ "$PYTHON_MINOR" -gt 11 ]; then
    echo "ERROR: Python $PYTHON_VERSION is not compatible with Atheris"
    echo "Atheris requires Python 3.8-3.11 (not 3.12+ due to PRECALL opcode changes)"
    echo "Base image should provide Python 3.11.13"
    exit 1
fi

echo "Python version $PYTHON_VERSION is compatible with Atheris"

# Install uv
pip3 install uv

# Install project dependencies (runtime only, no dev) into the system environment
cd $SRC/data_ingestor
uv pip install --system .

# Use OSS-Fuzz helper to compile Python fuzz targets
# This creates proper executables that ClusterFuzzLite recognizes
echo "Compiling Python fuzz targets with compile_python_fuzzer..."

compile_python_fuzzer fuzz/fuzz_pdf_parser.py
compile_python_fuzzer fuzz/fuzz_document_router.py
compile_python_fuzzer fuzz/fuzz_chunker.py

echo "=== Fuzzing Build Complete ==="
echo "Fuzz targets in $OUT:"
ls -la $OUT/ | grep -E "(fuzz_|^total|^d)"
echo "================================"
