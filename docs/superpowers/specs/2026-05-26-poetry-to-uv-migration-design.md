# Poetry to uv Migration Design (data_ingestor)

> Status: Approved design (brainstorming complete; awaiting implementation plan).
> Date: 2026-05-26.
> Fleet context: see `/home/byron/dev/poetry-to-uv-migration-guide.md`.
> Reference repos: `.claude`, `foundry_unify`.

## Goal

Migrate `data_ingestor` from Poetry to uv while taking the modernization opportunity to align with house style established in `.claude` and `foundry_unify`. The migration consolidates build backend, dependency declaration shape, CI delegation, and the Python tooling chain.

## Non-goals

- Rewriting the Dockerfile to a uv-native two-stage image. Deferred to a Phase 2 cleanup PR.
- Restructuring the `src/data_ingestor/` package layout.
- Changing any runtime behavior, public API, CLI, or test selection.
- Touching the ClusterFuzzLite fuzz target source files (only the build orchestration).

## High-level decisions

| Decision | Choice |
|---|---|
| Migration driver | Modernization opportunity (not strict parity, not minimal-effort) |
| PR strategy | Two PRs: manifest + local dev tooling, then CI + docs. Upgrade to single combined PR if `data_ingestor` is branch-protected |
| Build backend | `hatchling` |
| Dependency model | PEP 621 `[project.optional-dependencies]` extras for everything (dev, docs, azure, ml, advanced-pdf); `test` merged into `dev` |
| nox pattern | `nox-uv` plugin + `session.install("-e", DEV_EXTRAS)` |
| Safety package + supplemental index | Both dropped; `pip-audit` and Renovate cover the gap |
| Python management | uv-managed via `uv python install`; `.python-version` retained at `3.11` |
| Python range | `requires-python = ">=3.11,<3.15"` (floor unchanged, upper widened to house cap) |
| CI matrix | 3.11, 3.12, 3.13, 3.14 (4 jobs) |
| CI delegation | `ByronWilliamsCPA/.github/.github/workflows/python-ci.yml@<pinned-sha>` |
| CVE handling | `[tool.uv] override-dependencies = ["regex>=2025.2.10"]` paired with `uv lock --upgrade-package regex` |
| Renovate config | `enabledManagers = ["pep621", "github-actions", "pre-commit", "dockerfile"]`; validated via `renovate-config-validator` |
| Docker | Deferred to Phase 2 cleanup PR; only `scripts/generate_requirements.sh` changes in this migration |

## Architecture (post-migration state)

### Files modified or created

| File | Change |
|---|---|
| `pyproject.toml` | Full conversion: hatchling backend, PEP 621 dependencies, four extras, `[tool.uv]` block |
| `uv.lock` | New file; generated via `uv sync --all-extras && uv lock --upgrade`; committed |
| `poetry.lock` | Deleted |
| `.python-version` | Retained or created at `3.11` |
| `renovate.json` | `enabledManagers` updated; `poetry` removed; `pep621` added |
| `noxfile.py` | nox-uv plugin pattern; ~30 install calls converted |
| `Makefile` | `POETRY` → `UV`; black + safety targets removed in favor of ruff format + pip-audit |
| `docker-compose.yml` | Line 70 command swap: `poetry run pytest` → `uv run pytest` |
| `scripts/generate_requirements.sh` | `poetry export` → `uv export --format requirements-txt --hashes` |
| `.pre-commit-config.yaml` | Replace `psf/black` hook with `ruff-format`; drop any `poetry-check`/`poetry-lock`/`poetry-export` hooks |
| `.github/workflows/ci.yml` | Replaced with shared workflow call; 4-version matrix |
| `.github/workflows/pr-validation.yml` | Deleted (covered by shared workflow) |
| `.github/workflows/release.yml` | Poetry verbs swapped for uv |
| `.github/workflows/security-analysis.yml` | Poetry verbs swapped for uv |
| `.clusterfuzzlite/build.sh` | `pip3 install poetry` → `pip3 install uv` + sync flags |
| `CLAUDE.md` | All `poetry install` / `poetry run` references swapped; automated-testing pre-approval list updated |
| `README.md` | Quick Start updated with `uv python install` and `uv sync --all-extras` |
| `CONTRIBUTING.md` | Swapped if present |
| `SECURITY.md` | Updated if it references `safety` tool or Safety index |
| `docs/**/*.md` | Targeted swaps where install or run commands appear |

### Files NOT modified

| File | Why |
|---|---|
| `Dockerfile` | Already pip-based via `requirements-docker.txt`; rewrite deferred to Phase 2 cleanup PR |
| `src/**` | No source code changes |
| `tests/**` | No test changes |
| `fuzz/**` | Fuzz target source files unchanged; only `.clusterfuzzlite/build.sh` orchestration changes |
| `docs/PROJECT_PLAN.md` and similar content docs | Only updated if they contain install or run command examples |

## pyproject.toml shape after migration

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "data_ingestor"
version = "0.1.0"
description = "Custom data ingestion tool for use with RAG agents"
authors = [{name = "Byron", email = "byronawilliams@gmail.com"}]
license = {text = "MIT"}
readme = "README.md"
keywords = ["ai", "prompt-engineering", "mcp", "zen", "orchestration"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Programming Language :: Python :: 3.14",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
]
requires-python = ">=3.11,<3.15"
dependencies = [
    # ~50 entries lifted from [tool.poetry.dependencies], converted per Step 2 table
    "gradio>=5.35.0,<6.0.0",
    "fastapi>=0.116.0,<0.117.0",
    # ... full list during execution
]

[project.urls]
homepage = "https://github.com/Byron/data_ingestor"
repository = "https://github.com/Byron/data_ingestor"
documentation = "https://github.com/Byron/data_ingestor/wiki"

[project.scripts]
data-ingestor = "data_ingestor.cli.main:cli"

[project.optional-dependencies]
dev = [
    # merged dev + test groups, minus "safety"
    "pytest>=8.0.1",
    "pytest-asyncio>=0.26.0",
    "pytest-cov>=6.0.0",
    # ... full list during execution
]
docs = [
    "mkdocs>=1.6.0,<2.0.0",
    "mkdocs-material>=9.5.32,<10.0.0",
    "mkdocstrings[python]>=0.24.0,<1.0.0",
]
azure = [
    "azure-identity>=1.15.0,<2.0.0",
    "azure-keyvault-secrets>=4.8.0,<5.0.0",
    "azure-storage-blob>=12.19.0,<13.0.0",
]
ml = [
    "sentence-transformers>=3.0.0,<6.0.0",
    "tiktoken>=0.8.0,<1.0.0",
    "numpy>=1.26.1,<2.0.0",
    "pandas>=2.2.0,<3.0.0",
    "spacy>=3.7.0,<4.0.0",
    "nltk>=3.8.0,<4.0.0",
]
advanced-pdf = [
    "marker-pdf>=1.9.3,<2.0.0",
]

[tool.hatch.build.targets.wheel]
packages = ["src/data_ingestor"]

[tool.uv]
override-dependencies = ["regex>=2025.2.10"]   # pair with: uv lock --upgrade-package regex

# All existing [tool.ruff], [tool.mypy], [tool.pytest.ini_options],
# [tool.coverage.*], [tool.bandit], [tool.isort] blocks remain unchanged
# Existing [tool.black] block is removed (ruff format replaces black)
```

### Constraint conversion (caret to PEP 440)

Applied per the fleet guide's Step 2 table. Examples specific to `data_ingestor`:

| Current | Becomes |
|---|---|
| `gradio = "^5.35.0"` | `gradio>=5.35.0,<6.0.0` |
| `python-multipart = "^0.0.18"` | `python-multipart>=0.0.18,<0.0.19` |
| `httpx = "^0.27.0"` | `httpx>=0.27.0,<0.28.0` (preserve Poetry semantics; if widening, add comment) |
| `redis = {extras = ["hiredis"], version = "^6.0.0"}` | `redis[hiredis]>=6.0.0,<7.0.0` |
| `anthropic = ">=0.46.0,<1.0.0"` | unchanged (already PEP 440) |

## noxfile.py shape after migration

```python
"""Nox-UV sessions for testing, linting, and security checks."""

import contextlib

import nox

with contextlib.suppress(ImportError):
    import nox_uv  # noqa: F401 - Required for uv backend support

nox.options.sessions = ["unit", "lint", "typecheck"]
nox.options.reuse_existing_virtualenvs = True
nox.options.default_venv_backend = "uv"

PYTHON_VERSIONS = ["3.11", "3.12", "3.13", "3.14"]
DEV_EXTRAS = ".[dev]"


@nox.session(python=PYTHON_VERSIONS)
def unit(session):
    """Run unit tests (fast development cycle)."""
    session.install("-e", DEV_EXTRAS)
    session.run("pytest", "-m", "unit and not slow", *session.posargs)


# ... remaining sessions follow the same install + run pattern
```

All 28+ existing sessions get the same two-line install pattern in place of the Poetry install + `poetry run` indirection.

## Makefile shape after migration

```makefile
PYTHON := python3.12
UV     := uv

install:
	$(UV) sync --all-extras

setup: install
	$(UV) run pre-commit install
	./scripts/generate_requirements.sh
	$(UV) run python src/utils/encryption.py
	@echo "Development environment ready!"

# ... test, lint, format, security targets all use $(UV) run
# Notable changes from current state:
#   lint: drops "$(POETRY) run black --check ." (ruff format covers it)
#   format: drops "$(POETRY) run black ." (ruff format covers it)
#   security: drops "$(POETRY) run safety check"; adds "$(UV) run pip-audit"
```

## CI workflow shape after migration

`.github/workflows/ci.yml` collapses to roughly:

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    types: [opened, synchronize, reopened]
    branches: [main, develop]
  workflow_dispatch:

concurrency:
  group: ${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: true

permissions:
  contents: read
  pull-requests: write
  checks: write

jobs:
  ci:
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.11", "3.12", "3.13", "3.14"]
    uses: ByronWilliamsCPA/.github/.github/workflows/python-ci.yml@<pinned-sha>
    with:
      python-version: ${{ matrix.python-version }}
      coverage-threshold: 80
      source-directory: 'src'
      test-directory: 'tests'
```

Caveat: must verify the shared workflow accepts `python-version` from a caller-side matrix. If it does not, fall back to four parallel jobs with literal version values.

`release.yml` and `security-analysis.yml` stay bespoke but with Poetry verbs swapped for uv. `pr-validation.yml` is deleted.

## .clusterfuzzlite/build.sh shape after migration

```bash
#!/bin/bash -eu

# (Atheris constraint check unchanged; still requires Python 3.8-3.11)

pip3 install uv
cd $SRC/data_ingestor
uv sync --no-dev --no-editable --frozen --python python3.11
source .venv/bin/activate

# (compile_python_fuzzer invocations unchanged)
```

The Python 3.11 pin is intentional and constrained by Atheris, not by the migration. The 3.13/3.14 matrix entries do not run fuzzing.

## Renovate config shape after migration

```jsonc
{
  "enabledManagers": [
    "pep621",
    "github-actions",
    "pre-commit",
    "dockerfile"
  ],
  // ... all existing rules retained
}
```

Validated via `npx --yes --package renovate -- renovate-config-validator` before commit.

## PR slicing

### PR 1: manifest + local dev tooling

Branch: `chore/uv-migration-manifest`

Files:
- `pyproject.toml`
- `uv.lock` (created), `poetry.lock` (deleted), `.python-version` (created or retained at `3.11`)
- `renovate.json`
- `Makefile`
- `noxfile.py`
- `scripts/generate_requirements.sh`
- `docker-compose.yml` (line 70 command)
- `.pre-commit-config.yaml`

Acceptance:
- `uv sync --all-extras` resolves
- `uv lock --upgrade-package regex` produces the override-dependent lock
- `uv run pytest -m "not slow"` passes
- `nox --list-sessions` matches expected catalog
- `nox -s unit` runs end-to-end
- `make test-fast` runs end-to-end
- `renovate-config-validator` passes

### PR 2: CI + docs

Branch: `chore/uv-migration-ci-docs`

Files:
- `.github/workflows/ci.yml` (replaced)
- `.github/workflows/pr-validation.yml` (deleted)
- `.github/workflows/release.yml` (verbs swapped)
- `.github/workflows/security-analysis.yml` (verbs swapped)
- `.clusterfuzzlite/build.sh`
- `CLAUDE.md`, `README.md`, `CONTRIBUTING.md`, `SECURITY.md`
- `docs/**/*.md` (targeted swaps only)

Acceptance:
- CI runs green on draft PR across full 3.11-3.14 matrix
- Codecov upload appears on draft PR
- `git grep -i poetry -- ':!CHANGELOG.md' ':!docs/known-vulnerabilities.md' ':!docs/superpowers/specs/'` returns zero results
- ClusterFuzzLite manual run completes or matches pre-migration failure mode

### Branch-protection contingency

If `data_ingestor` has required status checks on `main`, the two-PR split fails because PR 1 leaves CI red. In that case, switch to:

- Option A: Combine PR 1 + minimal CI fix (just the `ci.yml` replacement) into one PR. Defer the rest of CI plus all docs to PR 2.

Confirm branch protection state at implementation time before opening PR 1.

## Validation checklist (per the fleet guide, plus data_ingestor specifics)

Run in order; any failure stops the migration on this repo:

- [ ] `uv sync --all-extras` resolves without errors
- [ ] `uv lock --upgrade-package regex` succeeds and produces an upgraded `regex` in `uv.lock`
- [ ] `uv.lock` is committed; `poetry.lock` is deleted; `.python-version` is `3.11`
- [ ] `npx --yes --package renovate -- renovate-config-validator` passes
- [ ] `uv run python -c "import data_ingestor"` succeeds
- [ ] `uv run pytest -m "not slow"` passes
- [ ] `uv run ruff check .` passes or matches pre-migration baseline
- [ ] `uv run pip-audit` runs (record findings; compare against baseline before blocking)
- [ ] `nox --list-sessions` lists expected sessions
- [ ] `nox -s unit` runs end-to-end
- [ ] `make test-fast` runs end-to-end
- [ ] CI runs green on draft PR (after PR 2)
- [ ] Codecov upload appears on draft PR (after PR 2)

## Rollback plan

| Scenario | Action |
|---|---|
| PR 1 merged, then `uv sync` fails on a contributor machine | `git revert` PR 1; restores `poetry.lock` and Makefile verbs |
| PR 1 merged, then a dep resolves differently and breaks runtime | `git revert` or pin the dep in `[tool.uv] override-dependencies` and forward-fix |
| PR 2 merged, then shared CI workflow misbehaves | `git revert` PR 2; PR 1 stays valid; local dev keeps working on uv |
| Deep regression after both PRs | Revert PR 2 first, then PR 1; gives a chance to fix CI in isolation |

PR ordering is chosen so PR 1 is reversible without re-breaking CI, and PR 2's CI changes can be validated against a known-good local environment.

## Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Fresh resolve picks a transitive that breaks runtime | Medium | Smoke test (`uv run pytest -m "not slow"`) before commit; widen `[tool.uv] override-dependencies` if needed |
| `marker-pdf` breaks with `regex>=2025.2.10` (the CVE override) | Medium | If `advanced-pdf` extra tests fail, drop the override and document the CVE risk in `docs/known-vulnerabilities.md` |
| Shared CI workflow does not support caller-side matrix | Low | Fall back to four parallel jobs with literal version values |
| Branch protection on `main` blocks PR 1 | Medium | Switch to Option A (combined PR 1 + minimal CI fix) |
| ClusterFuzzLite base image lacks uv | Low | `pip3 install uv` already in the build script |
| Renovate silently stops updating after merge | Medium | `renovate-config-validator` pre-merge plus 24-hour dashboard check post-merge |
| Pre-commit hooks reference removed packages (`black`, `safety`) | Low | Replace `psf/black` with `ruff-format`; remove any `safety` wrapper hooks during pre-commit config edit |

## Open questions for execution time

These are deliberately deferred until implementation (need a working checkout to answer):

1. Does `data_ingestor` have branch protection on `main`? If yes, switch to Option A PR strategy.
2. Does `SECURITY.md` reference `safety` or the Safety index? If yes, update it in PR 2.
3. Does the shared `python-ci.yml` reusable workflow accept caller-side matrix on `python-version`? If no, use four literal jobs.
4. What is the current pinned SHA for `ByronWilliamsCPA/.github/.github/workflows/python-ci.yml`? Fetch via `grep -RnE "python-ci\.yml@[a-f0-9]{40}" /home/byron/dev/foundry_unify/.github/workflows/`.
5. Does `.pre-commit-config.yaml` contain `poetry-check`, `poetry-lock`, or `poetry-export` hooks? Delete if found.
6. Does the current `generate_requirements.sh` exist and what does it contain? Rewrite or create per the migration guide.

## Out of scope (Phase 2 cleanup tickets)

- Dockerfile rewrite to uv-native two-stage image
- Stale `make dev` target reference to `docker-compose.zen-vm.yaml` (does not exist)
- Consolidation of `security-analysis.yml` against `.claude`'s equivalent workflow

## Next step

Invoke the writing-plans skill to produce a step-by-step implementation plan with explicit task ordering, dependency tracking, and validation gates between PR 1 and PR 2.
