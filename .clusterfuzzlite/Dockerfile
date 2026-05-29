# ClusterFuzzLite build container for Data Ingestor (Python / Atheris).
# Uses the OSS-Fuzz Python base image, which provides Atheris, the fuzzing
# toolchain, and the compile_python_fuzzer helper used by build.sh.
FROM gcr.io/oss-fuzz-base/base-builder-python

# Copy the repository into the OSS-Fuzz source tree.
COPY . $SRC/data_ingestor

# Install the build script where ClusterFuzzLite expects it.
COPY .clusterfuzzlite/build.sh $SRC/build.sh

WORKDIR $SRC/data_ingestor
