# Poetry to uv Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate `data_ingestor` from Poetry to uv across two PRs (manifest+local-dev, then CI+docs), aligning with house style established in `.claude` and `foundry_unify`.

**Architecture:** PEP 621 extras + hatchling build backend + `nox-uv` plugin + shared reusable CI workflow + Renovate `pep621` manager. Detailed design at [docs/superpowers/specs/2026-05-26-poetry-to-uv-migration-design.md](../specs/2026-05-26-poetry-to-uv-migration-design.md).

**Tech Stack:** uv, hatchling, nox, nox-uv, GitHub Actions reusable workflow at `ByronWilliamsCPA/.github/.github/workflows/python-ci.yml@e5ebf9e7f91603ffc5e2acc459460b50ba02016d`.

**Repository context:** Working directory for all commands is `/home/byron/dev/unify/data_ingestor`. All file paths in this plan are absolute or relative to that working directory.

---

## PR 1: Manifest + Local Dev Tooling

### Task 1: Pre-flight verification and baseline

**Files:**
- Verify: working tree, branch state, current `pyproject.toml`, current `Makefile`, current `noxfile.py`

- [ ] **Step 1: Confirm working directory and clean tree**

Run: `cd /home/byron/dev/unify/data_ingestor && git status`
Expected: working tree clean (or pre-existing changes you intend to keep separate from this migration)

- [ ] **Step 2: Check branch protection status on `main`**

Run: `gh api repos/Byron/data_ingestor/branches/main/protection 2>&1 | head -5`
Expected: either `"required_status_checks"` block (branch-protected) or `"Branch not protected"` / 404 error.

If branch-protected, mark this fact in the PR description and prepare for PR-strategy Option A (combine PR 1 + minimal CI fix). The plan below assumes the two-PR split; adjust the final commit of PR 1 to bundle Task 15 (ci.yml replacement) if needed.

- [ ] **Step 3: Capture baseline test count**

Run: `poetry install --sync && poetry run pytest -m "not slow" --collect-only -q 2>&1 | tail -5`
Expected: a count line like `1234 tests collected in N.NNs`. Record this number; we use it to confirm no test was lost.

- [ ] **Step 4: Create the PR 1 branch**

```bash
git checkout -b chore/uv-migration-manifest
```

Expected: switched to a new branch.

- [ ] **Step 5: Install uv if not already present**

```bash
command -v uv || curl -LsSf https://astral.sh/uv/install.sh | sh
uv --version
```

Expected: a version string like `uv 0.5.x` or newer.

- [ ] **Step 6: Install Python versions for the matrix**

```bash
uv python install 3.11 3.12 3.13 3.14
```

Expected: four versions installed. If 3.14 is unavailable as a stable release, retry with `--preview` or downgrade to `3.13` only and update Section 1 of the design to match.

- [ ] **Step 7: No commit yet** (this task only verifies state)

---

### Task 2: Rewrite `[build-system]` and skeleton `[project]` block

**Files:**
- Modify: `pyproject.toml:1-29`

- [ ] **Step 1: Open pyproject.toml and replace the top 30 lines**

Replace the existing `[build-system]` and `[project]` blocks. New content:

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
dependencies = []  # filled in Task 3

[project.urls]
homepage = "https://github.com/Byron/data_ingestor"
repository = "https://github.com/Byron/data_ingestor"
documentation = "https://github.com/Byron/data_ingestor/wiki"

[project.scripts]
data-ingestor = "data_ingestor.cli.main:cli"
```

Key changes from current state:
- `requires` switched to `hatchling`
- `dynamic = ["dependencies"]` removed
- `requires-python` widened from `>=3.11,<3.13` to `>=3.11,<3.15`
- Two new classifier lines for Python 3.13 and 3.14
- `[project.scripts]` block added (was under `[tool.poetry.scripts]`)
- `dependencies = []` placeholder; populated in Task 3

- [ ] **Step 2: Sanity check the TOML parses**

Run: `uv run python -c "import tomllib; tomllib.load(open('pyproject.toml', 'rb'))" 2>&1 | head -5`
Expected: no output (success) or a clear parse error pointing to a specific line if something was mis-edited.

Note: at this point `uv run` will still try to use Poetry's lockfile, which may fail. If it does, that is expected; the parse check can also be done with `python3 -c "import tomllib; ..."` directly using system Python.

- [ ] **Step 3: No commit yet** (manifest is mid-conversion)

---

### Task 3: Lift main dependencies into `[project] dependencies = [...]`

**Files:**
- Modify: `pyproject.toml` (the `dependencies = []` placeholder set in Task 2)

- [ ] **Step 1: Read the current `[tool.poetry.dependencies]` block**

Identify lines `40-118` of the current `pyproject.toml` (the `[tool.poetry.dependencies]` block, excluding the `python = ">=3.11,<3.13"` line which becomes `requires-python`).

- [ ] **Step 2: Convert each entry using the caret-to-PEP 440 table**

Use this conversion table:

| Poetry source | PEP 440 result |
|---|---|
| `^X.Y.Z` (X >= 1) | `>=X.Y.Z,<(X+1).0.0` |
| `^0.X.Y` | `>=0.X.Y,<0.(X+1).0` |
| `^0.0.Y` | `>=0.0.Y,<0.0.(Y+1)` |
| `~X.Y` | `>=X.Y,<X.(Y+1)` |
| `>=X,<Y` (already PEP 440) | unchanged |
| `{extras=["a"], version="^X.Y"}` | `pkg[a]>=X.Y,<(X+1).0.0` |

Apply to every entry. Examples:
- `gradio = "^5.35.0"` → `"gradio>=5.35.0,<6.0.0"`
- `python-multipart = "^0.0.18"` → `"python-multipart>=0.0.18,<0.0.19"`
- `httpx = "^0.27.0"` → `"httpx>=0.27.0,<0.28.0"`
- `redis = {extras = ["hiredis"], version = "^6.0.0"}` → `"redis[hiredis]>=6.0.0,<7.0.0"`
- `sqlalchemy = {extras = ["asyncio"], version = "^2.0.36"}` → `"sqlalchemy[asyncio]>=2.0.36,<3.0.0"`
- `pyjwt = {version = "^2.10.1", extras = ["crypto"]}` → `"pyjwt[crypto]>=2.10.1,<3.0.0"`
- `anthropic = ">=0.46.0,<1.0.0"` → `"anthropic>=0.46.0,<1.0.0"` (unchanged)
- `structlog = ">=24.0.0,<26.0.0"` → `"structlog>=24.0.0,<26.0.0"` (unchanged)
- `pillow = ">=10.1.0,<11.0.0"` → `"pillow>=10.1.0,<11.0.0"` (unchanged; existing comment about marker-pdf compatibility kept as `# comment` line above the entry)

- [ ] **Step 3: Replace `dependencies = []` with the full list**

The block should look like:

```toml
dependencies = [
    # Core web framework
    "gradio>=5.35.0,<6.0.0",
    "fastapi>=0.116.0,<0.117.0",
    "uvicorn[standard]>=0.35.0,<0.36.0",
    "httpx>=0.27.0,<0.28.0",
    "pydantic>=2.11.0,<3.0.0",
    "pydantic-settings>=2.2.1,<3.0.0",
    # LLM clients
    # Temporarily relaxed to allow marker-pdf compatibility (requires anthropic <0.47.0)
    "anthropic>=0.46.0,<1.0.0",
    "openai>=1.12.0,<2.0.0",
    # ... (apply the same conversion to every remaining entry from poetry.dependencies)
]
```

Preserve any inline comments from the original (e.g., the marker-pdf compatibility note).

- [ ] **Step 4: Sanity check the TOML parses**

Run: `python3 -c "import tomllib; data = tomllib.load(open('pyproject.toml', 'rb')); print(len(data['project']['dependencies']))"`
Expected: a count matching the number of entries you wrote (should be around 50).

- [ ] **Step 5: No commit yet**

---

### Task 4: Lift Poetry groups into `[project.optional-dependencies]`

**Files:**
- Modify: `pyproject.toml` (insert `[project.optional-dependencies]` block after `[project.scripts]`)

- [ ] **Step 1: Locate current group blocks**

Identify the following blocks in the current `pyproject.toml`:
- `[tool.poetry.group.dev.dependencies]` (lines ~119-150)
- `[tool.poetry.group.azure.dependencies]` (lines ~152-155)
- `[tool.poetry.group.ml.dependencies]` (lines ~157-163)
- `[tool.poetry.group.docs.dependencies]` (lines ~165-168)
- `[tool.poetry.group.test.dependencies]` (lines ~170-173)
- `[tool.poetry.group.advanced-pdf.dependencies]` (lines ~178-186)

- [ ] **Step 2: Write the four extras (dev absorbs test)**

Insert this block immediately after `[project.scripts]` and before any `[tool.*]` blocks:

```toml
[project.optional-dependencies]
dev = [
    # Testing (merged from former [tool.poetry.group.test.dependencies])
    "pytest>=8.0.1",
    "pytest-asyncio>=0.26.0",
    "pytest-cov>=6.0.0",
    "pytest-env>=1.1.3",
    "pytest-mock>=3.12.0",
    "pytest-timeout>=2.2.0",
    "pytest-xdist>=3.5.0",
    "pytest-rerunfailures>=12.0",
    "pytest-benchmark>=4.0.0",
    "pytest-memray>=1.5.0",
    "aiosqlite>=0.21.0,<0.22.0",
    "hypothesis>=6.98.9",
    "faker>=37.0.0",
    # Code quality
    "ruff==0.12.3",
    "mypy==1.13.0",
    "types-pyyaml>=6.0.12.12",
    "types-python-dateutil>=2.8.19.20240106",
    "types-aiofiles>=24.0.0",
    "types-cachetools>=6.1.0.20250717",
    # Security
    "bandit[toml]==1.7.7",
    "detect-secrets>=1.5.0",
    "pip-audit>=2.9.0,<3.0.0",
    # Dev tooling
    "pre-commit>=4.0.0",
    "nox>=2025.1.0",
    "nox-uv>=0.6.3",
    "ipython>=9.0.0",
    "ipdb>=0.13.13",
    "toml>=0.10.2,<0.11.0",
    "mutmut>=3.3.0,<4.0.0",
    "locust>=2.0.0,<3.0.0",
    "datasets>=4.4.0,<5.0.0",
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
    # WARNING: marker-pdf constrains regex to <2025.0.0 (CVE-2025-78558).
    # Use the [tool.uv] override-dependencies block to force a safe regex version.
    "marker-pdf>=1.9.3,<2.0.0",
]
```

Changes from current Poetry groups:
- `test` deps merged into `dev`
- `safety` dropped (replaced by `pip-audit` which is already in dev)
- `black` dropped (replaced by `ruff format`)
- `isort` dropped (replaced by Ruff's `I` rule)
- `nox-uv>=0.6.3` added
- All caret constraints converted to PEP 440 ranges per the Task 3 table

- [ ] **Step 3: Sanity check the TOML parses**

Run: `python3 -c "import tomllib; data = tomllib.load(open('pyproject.toml', 'rb')); print(list(data['project']['optional-dependencies'].keys()))"`
Expected: `['dev', 'docs', 'azure', 'ml', 'advanced-pdf']`

- [ ] **Step 4: No commit yet**

---

### Task 5: Add `[tool.uv]` override-dependencies + Hatchling wheel target

**Files:**
- Modify: `pyproject.toml` (insert before existing `[tool.black]` block, which will be removed in Task 6)

- [ ] **Step 1: Insert these two blocks before the first `[tool.*]` block**

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/data_ingestor"]

[tool.uv]
override-dependencies = ["regex>=2025.2.10"]   # CVE-2025-78558 ReDoS; pair with: uv lock --upgrade-package regex
```

- [ ] **Step 2: Sanity check the TOML parses**

Run: `python3 -c "import tomllib; data = tomllib.load(open('pyproject.toml', 'rb')); print(data['tool']['uv'])"`
Expected: `{'override-dependencies': ['regex>=2025.2.10']}`

- [ ] **Step 3: No commit yet**

---

### Task 6: Delete Poetry sections from pyproject.toml

**Files:**
- Modify: `pyproject.toml` (delete all `[tool.poetry*]` blocks plus `[tool.black]` and `[tool.isort]`)

- [ ] **Step 1: Delete the following blocks**

Remove these section headers and their contents from `pyproject.toml`:

- `[tool.poetry]` (around lines 33-35)
- `[tool.poetry.scripts]` (around lines 37-38) — already moved to `[project.scripts]` in Task 2
- `[tool.poetry.dependencies]` (around lines 40-118) — already moved to `[project] dependencies` in Task 3
- `[tool.poetry.group.dev.dependencies]` and all other group blocks — already moved to `[project.optional-dependencies]` in Task 4
- `[[tool.poetry.source]]` (around lines 189-192) — Safety index, dropped
- `[tool.black]` (around lines 194-214) — Ruff format replaces Black
- `[tool.isort]` (around lines 309-320) — Ruff `I` rule replaces isort

Keep these blocks unchanged:
- `[tool.ruff]`, `[tool.ruff.lint]`, `[tool.ruff.lint.per-file-ignores]`, `[tool.ruff.lint.pylint]`, `[tool.ruff.lint.isort]`
- `[tool.mypy]` and all its overrides
- `[tool.pydantic-mypy]`
- `[tool.pytest.ini_options]`
- `[tool.coverage.run]`, `[tool.coverage.report]`, `[tool.coverage.html]`, `[tool.coverage.xml]`
- `[tool.bandit]`, `[tool.bandit.assert_used]`
- `[tool.pytest.benchmark]`

- [ ] **Step 2: Sanity check the TOML parses**

Run: `python3 -c "import tomllib; data = tomllib.load(open('pyproject.toml', 'rb')); print('poetry' in data.get('tool', {}), 'black' in data.get('tool', {}), 'isort' in data.get('tool', {}))"`
Expected: `False False False` (no Poetry, no Black, no isort sections remaining).

- [ ] **Step 3: No commit yet**

---

### Task 7: Generate `uv.lock` and run smoke test

**Files:**
- Create: `uv.lock`
- Delete: `poetry.lock`
- Create or modify: `.python-version`

- [ ] **Step 1: Delete the Poetry lockfile**

```bash
git rm poetry.lock
```

Expected: `rm 'poetry.lock'`

- [ ] **Step 2: Create or update `.python-version`**

```bash
echo "3.11" > .python-version
git add .python-version
```

Expected: `.python-version` contains the single line `3.11`.

- [ ] **Step 3: Run initial sync**

```bash
uv sync --all-extras
```

Expected: a long resolution output, then `Resolved N packages in X.Xs` and `Installed N packages in X.Xs`. The `.venv` directory is created.

If resolution fails with a specific dependency conflict, read the error message; the most likely cause is a caret-to-PEP-440 conversion error from Task 3. Fix the offending entry and re-run.

- [ ] **Step 4: Refresh the lock to honor the CVE override**

```bash
uv lock --upgrade-package regex
```

Expected: `Resolved N packages in X.Xs`. Verify regex is now >= 2025.2.10:

```bash
grep -A1 '^name = "regex"' uv.lock | head -4
```

Expected: a `version = "2025.X.Y"` line where X.Y >= 2.10.

- [ ] **Step 5: Smoke test the install**

```bash
uv run python -c "import data_ingestor; print('OK')"
```

Expected: `OK`. If this fails with `ModuleNotFoundError: No module named 'data_ingestor'`, the hatchling wheel target in Task 5 may be misconfigured; verify `[tool.hatch.build.targets.wheel] packages = ["src/data_ingestor"]` is present.

- [ ] **Step 6: Run a fast test pass**

```bash
uv run pytest -m "not slow" --collect-only -q 2>&1 | tail -5
```

Expected: a test count matching the baseline from Task 1 Step 3. If the count is materially different (>5% drop), investigate before proceeding.

Then:

```bash
uv run pytest -m "unit and not slow" -x -q 2>&1 | tail -20
```

Expected: tests pass, or at most pre-existing failures that match the baseline.

- [ ] **Step 7: Commit the manifest + lockfile**

```bash
git add pyproject.toml uv.lock .python-version
git commit -m "chore(deps): convert pyproject.toml from Poetry to uv

- Replace poetry-core build backend with hatchling
- Lift dependencies to PEP 621 [project] dependencies
- Lift dependency groups to [project.optional-dependencies]:
  - dev (absorbs former test group)
  - docs, azure, ml, advanced-pdf
- Drop safety package and supplemental Safety index (pip-audit covers)
- Drop black and isort (replaced by ruff format + ruff I rule)
- Widen requires-python to >=3.11,<3.15 (house upper cap)
- Add [tool.uv] override-dependencies for regex CVE-2025-78558
- Generate uv.lock; delete poetry.lock
- Pin .python-version to 3.11 (lowest supported)

Design: docs/superpowers/specs/2026-05-26-poetry-to-uv-migration-design.md"
```

---

### Task 8: Update `renovate.json` for `pep621` manager

**Files:**
- Modify: `renovate.json`

- [ ] **Step 1: Add `enabledManagers` to the top level**

Open `renovate.json`. Add the following key to the top-level JSON object, immediately after `"extends": [...]`:

```jsonc
"enabledManagers": [
    "pep621",
    "github-actions",
    "pre-commit",
    "dockerfile"
],
```

- [ ] **Step 2: Update the "Python dependencies" rule description**

In the `packageRules` array, find the entry with description `"Python dependencies - Poetry managed"` and change it to:

```jsonc
"description": "Python dependencies - uv managed",
```

- [ ] **Step 3: Remove `safety` from the security-tooling matchPackageNames**

In the `packageRules` array, find the entry with description `"Security tooling - always update"`. The current `matchPackageNames` is `["bandit", "safety", "semgrep"]`. Change to:

```jsonc
"matchPackageNames": [
    "bandit",
    "pip-audit",
    "semgrep"
],
```

(`pip-audit` is added because it replaces safety's role.)

- [ ] **Step 4: Validate the config**

```bash
npx --yes --package renovate -- renovate-config-validator
```

Expected: `INFO: Validating renovate.json` followed by `INFO: Config validated successfully`. If validation fails, read the error message and fix.

- [ ] **Step 5: Commit**

```bash
git add renovate.json
git commit -m "chore(deps): switch Renovate to pep621 manager

- Add explicit enabledManagers (pep621, github-actions, pre-commit, dockerfile)
- Update Python dep rule description from 'Poetry managed' to 'uv managed'
- Replace safety with pip-audit in security-tooling matchPackageNames

Without explicit enabledManagers Renovate silently stops updating Python
deps when poetry sections disappear from pyproject.toml. See fleet guide
Step 3.5 for context (this trap has recurred four times)."
```

---

### Task 9: Rewrite `noxfile.py` with nox-uv pattern

**Files:**
- Modify: `noxfile.py` (full rewrite of header + every session's install line)

- [ ] **Step 1: Replace the noxfile.py header**

Replace the top of `noxfile.py` (everything before the first `@nox.session` decorator) with:

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
```

The `# noqa: F401 - Required for uv backend support` comment must be the full form; bare `# noqa: F401` trips Ruff `PGH004`.

- [ ] **Step 2: Replace every install call in every session**

For each `@nox.session` in the file, replace the install line:

```python
# Before
session.run("poetry", "install", "--with", "dev", external=True)

# After
session.install("-e", DEV_EXTRAS)
```

And:

```python
# Before
session.run("poetry", "install", external=True)

# After
session.install("-e", ".")
```

And:

```python
# Before
session.run("poetry", "show", "--outdated")

# After
# uv has no direct equivalent of "poetry show --outdated"; Renovate handles
# this. Delete the line or replace with: session.run("uv", "tree", external=True)
```

- [ ] **Step 3: Remove the `external=True` arguments**

Search for `external=True` in `noxfile.py`. Most occurrences are in `session.run("poetry", ...)` calls and disappear with Step 2. Any remaining `external=True` should be reviewed; nox runs `session.run` inside the session venv by default, so `external=True` is needed only for binaries genuinely outside the venv (rare).

- [ ] **Step 4: Verify noxfile is parseable**

```bash
uv run python -c "import nox; import importlib.util; spec = importlib.util.spec_from_file_location('noxfile', 'noxfile.py'); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); print('OK')"
```

Expected: `OK`. If a syntax error appears, fix it.

- [ ] **Step 5: List sessions**

```bash
uv run nox --list-sessions 2>&1 | head -30
```

Expected: a list of sessions matching what was in the file before (same names, same purposes). If sessions are missing, the header rewrite may have accidentally cut session definitions; revert and redo Step 1.

- [ ] **Step 6: Smoke test one session**

```bash
uv run nox -s unit -- --collect-only -q 2>&1 | tail -10
```

Expected: nox creates a venv with uv backend, installs dev extras, then collects tests. The collect-only output should match the baseline.

- [ ] **Step 7: Commit**

```bash
git add noxfile.py
git commit -m "chore(build): convert noxfile.py to nox-uv pattern

- Add nox-uv plugin import with ImportError suppression
- Set default_venv_backend='uv' and reuse_existing_virtualenvs=True
- Define PYTHON_VERSIONS for 3.11-3.14 matrix
- Replace every 'poetry install --with dev' with session.install('-e', DEV_EXTRAS)
- Replace every 'poetry run X' with bare 'X' (nox handles venv activation)"
```

---

### Task 10: Update `Makefile`

**Files:**
- Modify: `Makefile`

- [ ] **Step 1: Replace the variable declarations**

Replace:

```makefile
PYTHON := python3.11
POETRY := poetry
```

With:

```makefile
PYTHON := python3.12
UV     := uv
```

- [ ] **Step 2: Rewrite the install target**

Replace:

```makefile
install: ## Install dependencies with Poetry
	$(POETRY) install --sync
```

With:

```makefile
install: ## Install all dependencies (including extras)
	$(UV) sync --all-extras
```

- [ ] **Step 3: Update the setup target**

Replace:

```makefile
setup: install ## Complete development setup
	$(POETRY) run pre-commit install
	./scripts/generate_requirements.sh
	$(POETRY) run python src/utils/encryption.py
	@echo "Development environment ready!"
```

With:

```makefile
setup: install ## Complete development setup
	$(UV) run pre-commit install
	$(UV) run python src/utils/encryption.py
	@echo "Development environment ready!"
```

(The `generate_requirements.sh` line is removed because the script does not exist in the current repo.)

- [ ] **Step 4: Replace `$(POETRY) run` with `$(UV) run` everywhere else**

Use a single replacement pass:

```bash
sed -i 's/\$(POETRY) run/$(UV) run/g' Makefile
```

Verify:

```bash
grep -c "POETRY" Makefile
```

Expected: `0`.

- [ ] **Step 5: Drop the `black --check` and `black` invocations from lint and format targets**

In the `lint` target, find the line `$(UV) run black --check .` and delete it (Ruff format covers it).

In the `format` target, find the line `$(UV) run black .` and delete it.

Optionally add to `format`:

```makefile
format: ## Format code
	$(UV) run ruff format .
	$(UV) run ruff check --fix .
```

And mirror in `lint`:

```makefile
lint: ## Run linting checks
	$(UV) run ruff format --check .
	$(UV) run ruff check .
	$(UV) run mypy src
	markdownlint **/*.md
	yamllint .
```

- [ ] **Step 6: Update the security target**

Replace:

```makefile
security: ## Run security checks
	$(UV) run safety check
	$(UV) run bandit -r src
```

With:

```makefile
security: ## Run security checks
	$(UV) run pip-audit
	$(UV) run bandit -r src
```

- [ ] **Step 7: Smoke test the Makefile**

```bash
make help
```

Expected: the help target lists all available targets without errors.

```bash
make test-fast
```

Expected: pytest runs against `tests/unit/` and exits cleanly (or with pre-existing failures matching the baseline).

- [ ] **Step 8: Commit**

```bash
git add Makefile
git commit -m "chore(build): convert Makefile from poetry to uv

- POETRY variable renamed to UV
- 'poetry install --sync' replaced with 'uv sync --all-extras'
- 'poetry run X' replaced with 'uv run X' across all targets
- Drop black (Ruff format covers it) from lint/format targets
- Drop safety (use pip-audit) from security target
- Remove stale './scripts/generate_requirements.sh' from setup (script does not exist)"
```

---

### Task 11: Update `docker-compose.yml`

**Files:**
- Modify: `docker-compose.yml:70`

- [ ] **Step 1: Replace the test service command**

Find the line in the `test` service:

```yaml
    command: ["poetry", "run", "pytest", "-v", "--cov=src", "--cov-report=term-missing", "--cov-fail-under=80"]
```

Replace with:

```yaml
    command: ["uv", "run", "pytest", "-v", "--cov=src", "--cov-report=term-missing", "--cov-fail-under=80"]
```

- [ ] **Step 2: Verify yaml parses**

```bash
uv run python -c "import yaml; yaml.safe_load(open('docker-compose.yml'))" 2>&1 | head -3
```

Expected: no output (success).

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml
git commit -m "chore(build): swap poetry run for uv run in docker-compose test service

Note: the Dockerfile build itself does not yet contain uv; converting
docker-compose alone leaves the test service unable to run until the
Dockerfile is rewritten (deferred to a Phase 2 cleanup PR per the spec)."
```

---

### Task 12: PR 1 final validation

**Files:**
- Verify: full PR 1 working tree

- [ ] **Step 1: Confirm no Poetry references remain in PR 1 surface**

```bash
git grep -i poetry -- pyproject.toml Makefile noxfile.py docker-compose.yml renovate.json
```

Expected: no output. If output appears, address each occurrence.

- [ ] **Step 2: Run the validation checklist from the design**

```bash
uv sync --all-extras                                       # already done, but re-confirm
test -f uv.lock && echo "uv.lock present"                  # expected: "uv.lock present"
test ! -f poetry.lock && echo "poetry.lock removed"        # expected: "poetry.lock removed"
cat .python-version                                        # expected: "3.11"
npx --yes --package renovate -- renovate-config-validator  # expected: "Config validated successfully"
uv run python -c "import data_ingestor; print('OK')"       # expected: "OK"
uv run pytest -m "unit and not slow" -x -q 2>&1 | tail -3  # expected: passes or matches baseline
uv run nox --list-sessions | head                          # expected: session catalog
make test-fast                                             # expected: passes
```

- [ ] **Step 3: Push the branch**

```bash
git push -u origin chore/uv-migration-manifest
```

Expected: push succeeds; PR creation URL is printed.

- [ ] **Step 4: Open the PR**

```bash
gh pr create --title "chore(deps): migrate from Poetry to uv (manifest + local dev tooling)" \
  --body "$(cat <<'EOF'
## Summary

PR 1 of 2 for the Poetry to uv migration. This PR converts the manifest, lockfile, and local development tooling. CI workflows still reference poetry and are deliberately left to PR 2.

- Replace poetry-core with hatchling build backend
- Lift dependencies to PEP 621 (`[project] dependencies` + `[project.optional-dependencies]`)
- Drop safety package and supplemental Safety index (pip-audit + Renovate cover)
- Drop black and isort (replaced by ruff format + Ruff I rule)
- Widen requires-python to >=3.11,<3.15
- Add `[tool.uv] override-dependencies` for regex CVE-2025-78558
- Generate `uv.lock`; delete `poetry.lock`
- Pin `.python-version` to 3.11
- Convert `noxfile.py` to nox-uv pattern
- Convert `Makefile` poetry verbs to uv verbs
- Update `renovate.json` with explicit `enabledManagers = ["pep621", ...]`

Design: `docs/superpowers/specs/2026-05-26-poetry-to-uv-migration-design.md`
Fleet guide: `/home/byron/dev/poetry-to-uv-migration-guide.md`

## Test plan

- [x] `uv sync --all-extras` resolves
- [x] `uv lock --upgrade-package regex` produces regex>=2025.2.10
- [x] `uv run pytest -m "unit and not slow"` passes
- [x] `make test-fast` passes
- [x] `nox --list-sessions` matches expected catalog
- [x] `renovate-config-validator` passes
- [ ] CI deliberately left red until PR 2 lands

## Caveats

CI workflows in this PR still reference poetry and will fail. PR 2 (`chore/uv-migration-ci-docs`) replaces them with the shared reusable workflow. If branch protection requires green CI to merge, combine the minimal `ci.yml` replacement (Task 15) into this PR.

Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Expected: PR URL printed.

---

## PR 2: CI + Docs

### Task 13: Create PR 2 branch from PR 1 head

- [ ] **Step 1: Branch from the PR 1 branch tip**

```bash
git checkout -b chore/uv-migration-ci-docs chore/uv-migration-manifest
```

Expected: switched to new branch.

- [ ] **Step 2: No commit yet** (this task only sets up the branch)

---

### Task 14: Replace `.github/workflows/ci.yml` with shared workflow call

**Files:**
- Modify: `.github/workflows/ci.yml` (complete rewrite)

- [ ] **Step 1: Replace the entire file**

Overwrite `.github/workflows/ci.yml` with:

```yaml
# CI/CD Pipeline
# Delegates to the org-level reusable Python CI workflow.
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
    name: CI Pipeline
    uses: ByronWilliamsCPA/.github/.github/workflows/python-ci.yml@e5ebf9e7f91603ffc5e2acc459460b50ba02016d
    with:
      python-version: '3.12'
      coverage-threshold: 80
      source-directory: 'src'
      test-directory: 'tests'
      enable-matrix-testing: true
      python-versions-pr: '["3.11", "3.12"]'
      python-versions-comprehensive: '["3.11", "3.12", "3.13", "3.14"]'
      run-integration-tests: true
      run-security-tests: true
      enable-dead-code-check: true

  ci-gate:
    name: CI Gate
    runs-on: ubuntu-latest
    timeout-minutes: 5
    needs: [ci]
    if: always()
    steps:
      - name: Check CI results
        env:
          CI_RESULT: ${{ needs.ci.result }}
        run: |
          if [ "$CI_RESULT" != "success" ]; then
            echo "::error::CI Gate failed: CI result is $CI_RESULT"
            exit 1
          fi
          echo "CI Gate passed"
```

Notes:
- The shared workflow's tiered matrix is enabled via `enable-matrix-testing: true`
- PRs run against 3.11 and 3.12 (fast feedback); main/scheduled runs against the full 3.11-3.14 matrix
- The pinned SHA `e5ebf9e7f91603ffc5e2acc459460b50ba02016d` is the current HEAD of the org's `.github` workflows directory; Renovate (after PR 1's `pep621` change) will keep this fresh

- [ ] **Step 2: Verify the YAML parses**

```bash
uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))" 2>&1 | head -3
```

Expected: no output.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: replace bespoke ci.yml with shared reusable workflow

Delegates to ByronWilliamsCPA/.github/.github/workflows/python-ci.yml at
pinned SHA e5ebf9e7. Uses the workflow's built-in tiered matrix:

- python-versions-pr: 3.11, 3.12 (fast PR feedback)
- python-versions-comprehensive: 3.11, 3.12, 3.13, 3.14 (main/schedule)

The shared workflow handles uv setup, lint, typecheck, tests, coverage,
security scanning (bandit + pip-audit), dead code detection, and LLM
governance. Old bespoke ci.yml (~330 lines) collapses to ~50 lines."
```

---

### Task 15: Delete `.github/workflows/pr-validation.yml`

**Files:**
- Delete: `.github/workflows/pr-validation.yml`

- [ ] **Step 1: Delete the file**

```bash
git rm .github/workflows/pr-validation.yml
```

Expected: `rm '.github/workflows/pr-validation.yml'`.

- [ ] **Step 2: Commit**

```bash
git commit -m "ci: remove pr-validation.yml (covered by shared workflow)

The shared python-ci.yml reusable workflow includes dependency validation
and standards checks. The bespoke pr-validation.yml duplicated this."
```

---

### Task 16: Update `.github/workflows/release.yml`

**Files:**
- Modify: `.github/workflows/release.yml` (lines containing poetry references)

- [ ] **Step 1: Replace the Poetry install block**

Find the block that installs Poetry (around lines 41-90 based on discovery):

```yaml
- run: curl -sSL https://install.python-poetry.org | python3 -
  # ... PATH setup, poetry config, etc.
- run: poetry install --with dev --no-interaction
```

Replace with:

```yaml
- uses: astral-sh/setup-uv@08807647e7069bb48b6ef5acd8ec9567f424441b  # v8.1.0
  with:
    enable-cache: true
- run: uv sync --extra dev
```

The pinned SHA above is taken from `/home/byron/dev/.github/.github/workflows/python-*.yml`, which is the canonical fleet pin. Renovate (after PR 1's `pep621` change) will keep this fresh.

- [ ] **Step 2: Replace step-level command swaps**

| Find | Replace |
|---|---|
| `poetry run pytest ...` | `uv run pytest ...` |
| `poetry build` | `uv build` |
| `"prepareCmd": "poetry version ${nextRelease.version}"` | `"prepareCmd": "uv version ${nextRelease.version}"` |

For `uv version`: this command exists in uv 0.5+ and writes `[project] version` in pyproject.toml. If the runner uses an older uv version, fall back to:

```jsonc
"prepareCmd": "sed -i 's/^version = .*/version = \"${nextRelease.version}\"/' pyproject.toml"
```

- [ ] **Step 3: Update the egress allowlist**

Find any `install.python-poetry.org:443` entry in egress-policy or harden-runner config and remove it. uv installs from `astral.sh` or via the setup-uv action; no extra egress entry usually needed.

- [ ] **Step 4: Drop poetry cache entries**

Find:

```yaml
- uses: actions/cache@...
  with:
    path: |
      .venv
      ~/.cache/pypoetry
    key: release-poetry-...
```

Either delete (setup-uv has `enable-cache: true` built in) or replace the path/key with `~/.cache/uv` and `release-uv-${{ runner.os }}-${{ hashFiles('uv.lock') }}`.

- [ ] **Step 5: Verify the YAML parses**

```bash
uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml'))" 2>&1 | head -3
```

Expected: no output.

- [ ] **Step 6: Confirm no poetry references remain**

```bash
grep -c "poetry" .github/workflows/release.yml
```

Expected: `0`.

- [ ] **Step 7: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci: convert release.yml from poetry to uv

- Replace poetry install with astral-sh/setup-uv@v5.1.0 (pinned SHA)
- Replace 'poetry build' with 'uv build'
- Replace 'poetry run X' with 'uv run X'
- Replace semantic-release prepareCmd 'poetry version' with 'uv version'
- Remove install.python-poetry.org egress entry
- Replace poetry cache with uv cache (via setup-uv enable-cache: true)"
```

---

### Task 17: Update `.github/workflows/security-analysis.yml`

**Files:**
- Modify: `.github/workflows/security-analysis.yml` (lines containing poetry references)

- [ ] **Step 1: Replace each Poetry install block**

There are three Poetry install blocks in this file (lines ~74-87, ~165-176, and the dependency-security job around line 84). For each block:

```yaml
# Before
- run: curl -sSL https://install.python-poetry.org | python3 -
  # ... config lines
- run: poetry install --only main --no-interaction
# or
- run: poetry install --with dev --no-interaction
```

Replace with:

```yaml
- uses: astral-sh/setup-uv@4db96194c378173c656ce18a155ffc14a9fc4355  # v5.1.0
  with:
    enable-cache: true
- run: uv sync --no-dev      # for --only main equivalents
# or
- run: uv sync --extra dev   # for --with dev equivalents
```

- [ ] **Step 2: Replace command-level swaps**

| Find | Replace |
|---|---|
| `poetry run python -c "..."` | `uv run python -c "..."` |
| `poetry run bandit -r src ...` | `uv run bandit -r src ...` |
| `poetry.lock` (in `paths` triggers) | `uv.lock` |

- [ ] **Step 3: Drop the safety invocation if present**

Find any `poetry run safety check` or `safety check` invocation. Replace with:

```yaml
- run: uv run pip-audit --strict
```

- [ ] **Step 4: Verify the YAML parses**

```bash
uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/security-analysis.yml'))" 2>&1 | head -3
```

Expected: no output.

- [ ] **Step 5: Confirm no poetry references remain**

```bash
grep -c "poetry" .github/workflows/security-analysis.yml
```

Expected: `0`.

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/security-analysis.yml
git commit -m "ci: convert security-analysis.yml from poetry to uv

- Replace three Poetry install blocks with setup-uv + uv sync
- Replace 'poetry run X' with 'uv run X'
- Replace safety with pip-audit
- Update path triggers from poetry.lock to uv.lock"
```

---

### Task 18: Update `.clusterfuzzlite/build.sh`

**Files:**
- Modify: `.clusterfuzzlite/build.sh`

- [ ] **Step 1: Replace the install block**

Find:

```bash
# Install Poetry
pip3 install poetry

# Install project dependencies (without dev dependencies)
cd $SRC/data_ingestor
poetry config virtualenvs.create false
poetry install --without dev --no-interaction
```

Replace with:

```bash
# Install uv
pip3 install uv

# Install project dependencies (without dev dependencies)
cd $SRC/data_ingestor
uv sync --no-dev --no-editable --frozen --python python3.11
source .venv/bin/activate
```

The `--python python3.11` is intentional: Atheris requires Python 3.8-3.11 (the script's existing version check enforces this).

- [ ] **Step 2: Verify the script is still executable**

```bash
test -x .clusterfuzzlite/build.sh && echo "executable" || echo "not executable"
```

If "not executable", run `chmod +x .clusterfuzzlite/build.sh`.

- [ ] **Step 3: Sanity check the script syntax**

```bash
bash -n .clusterfuzzlite/build.sh && echo "syntax OK"
```

Expected: `syntax OK`.

- [ ] **Step 4: Commit**

```bash
git add .clusterfuzzlite/build.sh
git commit -m "ci: convert ClusterFuzzLite build.sh from poetry to uv

- Replace 'pip3 install poetry' with 'pip3 install uv'
- Replace 'poetry install --without dev' with 'uv sync --no-dev --no-editable --frozen'
- Pin --python python3.11 explicitly (Atheris requires 3.8-3.11)
- Activate .venv before compile_python_fuzzer invocations"
```

---

### Task 19: Update `CLAUDE.md`

**Files:**
- Modify: `CLAUDE.md` (multiple sections)

- [ ] **Step 1: Replace install commands**

Use a controlled sed pass for the mechanical swaps:

```bash
sed -i \
  -e 's|poetry install --sync|uv sync --all-extras|g' \
  -e 's|poetry install --with dev|uv sync --extra dev|g' \
  -e 's|poetry install --with advanced-pdf|uv sync --extra advanced-pdf|g' \
  -e 's|poetry install|uv sync|g' \
  -e 's|poetry run |uv run |g' \
  CLAUDE.md
```

- [ ] **Step 2: Replace the "Code Quality" section's individual linter commands**

Find the block:

```bash
poetry run black .
poetry run ruff check --fix .
poetry run mypy src
```

After the sed pass above, it now reads:

```bash
uv run black .
uv run ruff check --fix .
uv run mypy src
```

Replace `uv run black .` with `uv run ruff format .`:

```bash
sed -i 's|uv run black \.|uv run ruff format .|g' CLAUDE.md
sed -i 's|uv run black --check \.|uv run ruff format --check .|g' CLAUDE.md
```

- [ ] **Step 3: Replace `safety check` with `pip-audit`**

```bash
sed -i 's|uv run safety check|uv run pip-audit|g' CLAUDE.md
```

- [ ] **Step 4: Update the "Automated Testing Configuration" pre-approval list**

Find the section header "Pre-Approved Test Commands" and the bullet list mentioning `poetry run pytest`. The sed pass already swapped these; verify by re-reading the section and confirming all bullets say `uv run pytest`.

- [ ] **Step 5: Update the "Python Version" section if it references 3.11/3.12 only**

Find any text like "Requires Python 3.11 or 3.12 (specified in pyproject.toml)" and update to "Requires Python 3.11+ (3.11, 3.12, 3.13, or 3.14; specified in pyproject.toml)".

- [ ] **Step 6: Verify no poetry references remain**

```bash
grep -in "poetry" CLAUDE.md | head
```

Expected: zero output. If any line is found, evaluate whether it's a historical mention (e.g., "We migrated from Poetry") or a missed command swap; address each.

- [ ] **Step 7: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(claude): swap poetry commands for uv equivalents

- Replace 'poetry install' / 'poetry run' with uv equivalents throughout
- Replace 'black .' with 'ruff format .'
- Replace 'safety check' with 'pip-audit'
- Update Python version mention to reflect 3.11-3.14 matrix"
```

---

### Task 20: Update `README.md`

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Apply the same sed pass**

```bash
sed -i \
  -e 's|poetry install --sync|uv sync --all-extras|g' \
  -e 's|poetry install --with dev|uv sync --extra dev|g' \
  -e 's|poetry install --with advanced-pdf|uv sync --extra advanced-pdf|g' \
  -e 's|poetry install|uv sync|g' \
  -e 's|poetry run |uv run |g' \
  -e 's|uv run black \.|uv run ruff format .|g' \
  -e 's|uv run safety check|uv run pip-audit|g' \
  README.md
```

- [ ] **Step 2: Add `uv python install` to the Quick Start**

Find the Quick Start or Installation section. Before the first `uv sync` invocation, add:

```markdown
1. Install uv if not already present:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
2. Install Python:
   ```bash
   uv python install 3.12
   ```
3. Sync dependencies:
   ```bash
   uv sync --all-extras
   ```
```

- [ ] **Step 3: Verify no poetry references remain**

```bash
grep -in "poetry" README.md | head
```

Expected: zero output, or only historical mentions in a Changelog/History section if such a section exists.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs(readme): swap poetry for uv in Quick Start and references"
```

---

### Task 21: Update `docs/**/*.md` (targeted)

**Files:**
- Modify: any file in `docs/` that contains install or run commands

- [ ] **Step 1: Find candidate files**

```bash
grep -rln "poetry " docs/ 2>/dev/null
```

Expected: a list of zero or more files. If empty, this task is a no-op; skip to Task 22.

- [ ] **Step 2: For each file, apply the same sed pass**

```bash
for f in $(grep -rln "poetry " docs/); do
  sed -i \
    -e 's|poetry install --sync|uv sync --all-extras|g' \
    -e 's|poetry install --with dev|uv sync --extra dev|g' \
    -e 's|poetry install --with advanced-pdf|uv sync --extra advanced-pdf|g' \
    -e 's|poetry install|uv sync|g' \
    -e 's|poetry run |uv run |g' \
    "$f"
done
```

- [ ] **Step 3: Manual review pass**

Run `grep -in "poetry" docs/` again and read each remaining match in context. If it's a historical mention (e.g., a migration note in an ADR), leave it. If it's an active install/run command, fix it.

- [ ] **Step 4: Commit**

```bash
git add docs/
git commit -m "docs: swap poetry for uv in installation and command examples"
```

If `git diff --cached` shows no changes (because no poetry references existed in docs/), skip the commit.

---

### Task 22: PR 2 final validation and creation

- [ ] **Step 1: Confirm no Poetry references remain in PR 2 surface**

```bash
git grep -i poetry -- ':!CHANGELOG.md' ':!docs/known-vulnerabilities.md' ':!docs/superpowers/'
```

Expected: zero output. The `docs/superpowers/` exclusion is for the design and plan docs that intentionally describe the migration. If other historical mentions exist (e.g., ADRs documenting prior choices), evaluate each and either preserve as historical or update if outdated.

- [ ] **Step 2: Verify all workflow YAML parses**

```bash
for f in .github/workflows/*.yml; do
  uv run python -c "import yaml, sys; yaml.safe_load(open(sys.argv[1])); print(f'{sys.argv[1]}: OK')" "$f"
done
```

Expected: every file reports `OK`.

- [ ] **Step 3: Push the branch**

```bash
git push -u origin chore/uv-migration-ci-docs
```

- [ ] **Step 4: Open PR 2**

```bash
gh pr create --title "chore(ci): migrate Poetry to uv (CI workflows + docs)" \
  --body "$(cat <<'EOF'
## Summary

PR 2 of 2 for the Poetry to uv migration. This PR converts the CI workflows, fuzzing build, and documentation. PR 1 (#REPLACE_WITH_PR1_NUMBER) must merge first.

- Replace bespoke `ci.yml` with shared `python-ci.yml` reusable workflow (pinned SHA `e5ebf9e7`)
- Use the shared workflow's built-in tiered matrix (3.11+3.12 on PRs, 3.11-3.14 on main/schedule)
- Delete `pr-validation.yml` (covered by shared workflow)
- Convert `release.yml` and `security-analysis.yml` from poetry verbs to uv verbs
- Convert `.clusterfuzzlite/build.sh` to use uv (preserves Python 3.11 pin for Atheris)
- Swap `CLAUDE.md`, `README.md`, and `docs/**/*.md` poetry references for uv

Design: `docs/superpowers/specs/2026-05-26-poetry-to-uv-migration-design.md`

## Test plan

- [ ] CI runs green on draft PR across full 3.11-3.14 matrix
- [ ] Codecov upload appears on draft PR
- [ ] `git grep -i poetry` returns zero results (excluding historical docs)
- [ ] ClusterFuzzLite manual run completes or matches pre-migration baseline

Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Expected: PR URL printed.

- [ ] **Step 5: Mark PR 2 as stacked on PR 1**

Edit the PR body to add the cross-link:

```bash
gh pr edit --body "Stacked on #PR1_NUMBER. Merge PR 1 first."
```

---

## Post-merge: cleanup tickets to file

After both PRs merge, create three follow-up tickets (out of scope for this migration):

- [ ] **Cleanup 1: Dockerfile rewrite to uv-native two-stage image** (deferred per design)
- [ ] **Cleanup 2: Stale `make dev` target references missing `docker-compose.zen-vm.yaml`**
- [ ] **Cleanup 3: Consolidation of `security-analysis.yml` against `.claude`'s equivalent workflow**

File these in the project tracker with a one-line description each and a link to this plan.

---

## Rollback procedure

| Situation | Action |
|---|---|
| PR 1 fails CI in a way that blocks merge | If branch-protected, combine PR 1 + Task 14 (ci.yml) into a single PR and reopen |
| PR 1 merged, contributor reports `uv sync` failure | `gh pr create` a hotfix PR pinning the failing dep in `[tool.uv] override-dependencies`; if unfixable, `git revert <PR1_merge_sha>` |
| PR 2 merged, CI green but ClusterFuzzLite breaks | `git revert` only the `.clusterfuzzlite/build.sh` commit; fuzz target source files are untouched, so revert is clean |
| Both PRs merged, deep regression | Revert PR 2 first, then PR 1; PR 1 alone keeps local dev working on uv |
