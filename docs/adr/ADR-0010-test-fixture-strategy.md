# ADR-0010: Test Fixture Strategy (GCS/Symlinks)

**Status**: Accepted
**Date**: 2025-11-17
**Deciders**: Claude Code, Project Lead
**Technical Story**: Sprint 0.3 - Test Data Generation Strategy

## Context and Problem Statement

Project B requires comprehensive test data to validate layout detection, OCR, structure assembly, and end-to-end pipeline functionality. Test data includes page images (PNG/JPG), DocumentMetadata JSON files, and expected OCRDocument JSON outputs. However, duplicating large datasets (DocLayNet: 81,471 documents, PubTables-1M: 1 million tables) across Projects A, B, C, D creates storage bloat and maintenance burden.

How should we structure test fixtures to enable comprehensive testing while avoiding data duplication, minimizing storage usage, and maintaining a single source of truth for benchmark datasets?

## Decision Drivers

* **Avoid Data Duplication**: DocLayNet (80GB) + PubTables (150GB) should not be copied across 4 projects
* **Single Source of Truth**: Benchmark datasets should be stored once, referenced everywhere
* **Storage Efficiency**: Minimize test fixture storage (<5GB for synthetic fixtures)
* **Test Coverage**: Enable unit, integration, component, and e2e tests across all scenarios
* **Fast Test Execution**: Unit tests should run in <1 minute (minimal I/O overhead)
* **Maintenance Burden**: Minimize effort to update test fixtures as schemas evolve
* **CI/CD Compatibility**: Test fixtures must work in GitHub Actions (no external dependencies)
* **Developer Experience**: Easy to add new test cases without complex setup

## Considered Options

* **Option 1: GCS Paths + Symlinks + Synthetic Fixtures** - Hybrid approach (recommended)
* **Option 2: Duplicate All Datasets** - Copy DocLayNet/PubTables to each project
* **Option 3: Git Submodules** - Share datasets via git submodules
* **Option 4: Copy-on-Write** - Hard links to shared dataset directory
* **Option 5: Synthetic Only** - Generate all test data programmatically

## Decision Outcome

**Chosen option**: "Option 1: GCS Paths + Symlinks + Synthetic Fixtures", because it provides the optimal balance of storage efficiency (no duplication), test coverage (real + synthetic data), and maintenance simplicity (single source of truth). Real benchmark datasets remain in GCS, symlinks reference Project A's image generator fixtures, and minimal synthetic fixtures cover unit testing.

### Implementation Details

1. **Test Fixture Structure**:
   ```
   src/project_b/tests/fixtures/
   ├── synthetic/              # Minimal synthetic fixtures (< 5MB)
   │   ├── simple_document.png
   │   ├── simple_metadata.json
   │   ├── expected_ocr_output.json
   │   └── ...
   ├── image_generator/        # Symlink to Project A image generator
   │   └── -> ../../../../project-a-preprocessing/tests/fixtures/generated_images/
   ├── benchmark_datasets/     # GCS paths only (no local storage)
   │   ├── doclaynet.json      # {"gcs_path": "gs://benchmarks/DocLayNet/", ...}
   │   └── pubtables.json      # {"gcs_path": "gs://benchmarks/PubTables/", ...}
   └── README.md               # Documentation of fixture strategy
   ```

2. **Synthetic Fixtures** (Unit Tests):
   ```python
   # tests/unit/test_layout_detection.py
   from project_b.tests.fixtures import load_synthetic_fixture

   def test_yolov10_simple_document():
       image = load_synthetic_fixture("simple_document.png")
       layout_blocks = detect_layout(image)
       assert len(layout_blocks) == 5
   ```

3. **Symlinked Fixtures** (Integration Tests):
   ```python
   # tests/integration/test_ocr_pipeline.py
   from project_b.tests.fixtures import load_generated_image

   def test_marker_ocr_on_generated_table():
       # Symlink to Project A image generator
       image = load_generated_image("table_complex_merged_cells.png")
       ocr_result = run_ocr_pipeline(image)
       assert ocr_result.teds_score > 0.95
   ```

4. **GCS Fixtures** (E2E Tests):
   ```python
   # tests/e2e/test_doclaynet_benchmark.py
   from project_b.tests.fixtures import load_benchmark_config

   @pytest.mark.slow
   @pytest.mark.e2e
   def test_doclaynet_validation_set():
       config = load_benchmark_config("doclaynet.json")
       gcs_path = config["gcs_path"]  # gs://benchmarks/DocLayNet/
       results = run_benchmark(gcs_path, limit=100)
       assert results["map_0.50"] > 0.82
   ```

### Positive Consequences

* **Zero Duplication**: DocLayNet/PubTables stored once in GCS, referenced by all projects
* **Storage Efficiency**: Test fixtures <5GB (synthetic only), vs. 230GB if duplicated
* **Single Source of Truth**: Benchmark datasets managed centrally (no drift)
* **Fast Unit Tests**: Synthetic fixtures load instantly (<1ms) from local filesystem
* **Comprehensive Coverage**: Synthetic (unit), generated (integration), real (e2e)
* **Easy Maintenance**: Update synthetic fixtures directly, symlinks auto-update
* **CI/CD Compatible**: Synthetic fixtures in git, GCS tests marked as `@pytest.mark.slow`

### Negative Consequences

* **Symlink Setup**: Developers must create symlinks manually on first setup
* **GCS Dependency**: E2E tests require GCS access (credentials setup)
* **Multi-Repo Coordination**: Symlinks assume Project A and B in same parent directory
* **Limited Synthetic Coverage**: Synthetic fixtures cannot cover all edge cases
* **Documentation Burden**: Must document fixture setup process clearly

## Pros and Cons of the Options

### Option 1: GCS Paths + Symlinks + Synthetic Fixtures

**Pros:**
* Good, because it eliminates data duplication (DocLayNet/PubTables stored once)
* Good, because storage efficiency is excellent (<5GB vs. 230GB)
* Good, because single source of truth prevents dataset drift
* Good, because fast unit tests (synthetic fixtures load instantly)
* Good, because comprehensive coverage (synthetic + generated + real)
* Good, because symlinks auto-update when Project A fixtures change
* Good, because CI/CD friendly (synthetic fixtures in git, GCS tests optional)

**Cons:**
* Bad, because symlink setup requires manual step on first clone
* Bad, because GCS access required for e2e tests (credentials setup)
* Bad, because multi-repo coordination assumes specific directory structure
* Bad, because documentation overhead to explain fixture strategy

### Option 2: Duplicate All Datasets

**Pros:**
* Good, because zero external dependencies (all data local)
* Good, because simple setup (git clone, no symlinks)
* Good, because fast test execution (all data on local SSD)
* Good, because no GCS credentials required

**Cons:**
* Bad, because massive storage bloat (230GB × 4 projects = 920GB)
* Bad, because git repository size explodes (LFS required, slow clones)
* Bad, because dataset updates must be synchronized across 4 projects
* Bad, because drift risk (Projects A, B, C, D may have different dataset versions)
* Bad, because CI/CD runners require massive disk space

### Option 3: Git Submodules

**Pros:**
* Good, because datasets stored once (in separate repository)
* Good, because version control for datasets (git history)
* Good, because no external cloud dependency (pure git solution)

**Cons:**
* Bad, because git submodules are notoriously difficult to use
* Bad, because large datasets in git are problematic (even with LFS)
* Bad, because submodule updates require careful synchronization
* Bad, because nested submodules increase complexity
* Bad, because CI/CD configuration becomes complex (recursive clone)

### Option 4: Copy-on-Write (Hard Links)

**Pros:**
* Good, because zero storage duplication (hard links share inodes)
* Good, because fast access (local filesystem)
* Good, because transparent to application code (looks like regular files)

**Cons:**
* Bad, because hard links only work on same filesystem (no cross-disk)
* Bad, because fragile (breaking link creates duplication)
* Bad, because doesn't work on Windows (NTFS junction points required)
* Bad, because difficult to track which files are hard-linked
* Bad, because CI/CD runners may not support hard links

### Option 5: Synthetic Only

**Pros:**
* Good, because zero external dependencies (all data generated)
* Good, because zero storage overhead (generated on-the-fly)
* Good, because easy to version control (Python code, not binary data)
* Good, because infinite test case generation (parametric tests)

**Cons:**
* Bad, because synthetic data cannot replicate real-world edge cases
* Bad, because benchmark validation requires real datasets (DocLayNet, PubTables)
* Bad, because generated images may not match production distribution
* Bad, because significant development effort to create realistic generators
* Bad, because difficult to reproduce production bugs without real data

## Links

* [Related to] [ADR-0009: GCS for Image Storage](ADR-0009-gcs-image-storage.md) - GCS provides centralized dataset storage
* [Related to] Project A: Image generator produces diverse test images
* [References] [src/project_b/tests/fixtures/README.md](../../src/project_b/tests/fixtures/README.md) - Fixture documentation
* [References] DocLayNet Dataset: 81,471 documents, 80GB (GCS: `gs://benchmarks/DocLayNet/`)
* [References] PubTables-1M: 1 million tables, 150GB (GCS: `gs://benchmarks/PubTables/`)

---

## Notes

**Fixture Storage Breakdown**:

| Fixture Type | Storage Location | Size | Test Coverage |
|-------------|------------------|------|---------------|
| Synthetic | `tests/fixtures/synthetic/` | <5MB | Unit tests (60%) |
| Generated (symlink) | `-> project-a/.../generated_images/` | 0MB (symlink) | Integration (30%) |
| Benchmark (GCS) | `gs://benchmarks/DocLayNet/` | 80GB (remote) | E2E (10%) |

**Total Local Storage**: <5MB (vs. 230GB if duplicated)

**Symlink Setup** (one-time per developer):

```bash
# Assuming project structure:
# workspace/
# ├── project-a-preprocessing/
# └── project-b-layout-ocr/

cd project-b-layout-ocr/src/project_b/tests/fixtures/
ln -s ../../../../project-a-preprocessing/tests/fixtures/generated_images/ image_generator

# Verify symlink
ls -la image_generator/
# -> ../../../../project-a-preprocessing/tests/fixtures/generated_images/
```

**Synthetic Fixture Categories**:

| Category | Count | Examples | Purpose |
|----------|-------|----------|---------|
| Simple Documents | 5 | 1-column text, single heading | Basic functionality |
| Complex Layouts | 8 | Multi-column, tables, figures | Layout detection |
| Degraded Images | 6 | Blur, noise, skew | OCR robustness |
| Edge Cases | 10 | Handwriting, formulas, watermarks | Error handling |
| **Total** | **29** | **<5MB** | **Unit testing** |

**Generated Image Fixtures** (via symlink):

| Category | Count | Generator | Purpose |
|----------|-------|-----------|---------|
| Tables | 50 | Project A table generator | Table structure |
| Multi-column | 30 | Project A layout generator | Reading order |
| Formulas | 20 | Project A formula generator | OCR accuracy |
| **Total** | **100** | **200MB** | **Integration testing** |

**Benchmark Dataset Configuration** (`benchmark_datasets/doclaynet.json`):

```json
{
  "name": "DocLayNet",
  "version": "1.1",
  "gcs_path": "gs://benchmarks/DocLayNet/",
  "splits": {
    "train": 64864,
    "val": 6489,
    "test": 10118
  },
  "annotations_path": "gs://benchmarks/DocLayNet/COCO/",
  "classes": 11,
  "size_gb": 80
}
```

**CI/CD Strategy**:

```yaml
# .github/workflows/tests.yml
jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: pytest tests/unit/  # Uses synthetic fixtures only

  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: |
          # Symlink to cached Project A fixtures
          ln -s /tmp/project-a-fixtures tests/fixtures/image_generator
      - run: pytest tests/integration/

  e2e-tests:
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      - run: |
          # Set up GCS credentials
          echo "${{ secrets.GCS_KEY }}" > /tmp/gcs-key.json
          export GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcs-key.json
      - run: pytest tests/e2e/ -m "not slow"
```

**Future Consideration**: If Project A and B diverge into separate repositories, convert symlinks to git submodule or shared fixture package (PyPI).
