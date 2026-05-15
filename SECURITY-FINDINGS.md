# Security Review — `data_ingestor`

Scope: file-processing pipeline, PDF parsing/injection, secrets & PII handling,
HTTP/API auth, and GitHub Actions hardening. Findings below were produced by
four parallel exploration passes (file-processing, PDF/crypto/PII, API surface,
GitHub Actions) and then triaged against the source before fixes were applied.

Severity is judged against the **actual current threat model** (local
CLI tool; no HTTP server exists yet; per-format file size cap already at 500 MB).
A finding rated lower than the audit's initial impression is annotated with
*"Reclassified"* and a justification.

## Summary

| # | Area | Finding | Severity | Status |
|---|------|---------|----------|--------|
| 1 | Resource limits | `f.read()` loads whole file into memory for SHA-256 dedup | **High** | Fixed |
| 2 | PDF injection | Unbounded / unsanitized PDF metadata fields propagate to JSON / YAML output | **High** | Fixed |
| 3 | Temp files | Predictable `time.time()`-based temp filename for upscaled PDFs (TOCTOU on shared host) | Medium | Fixed |
| 4 | Temp files | Temp PNG leaks if `insert_image()` raises during page upscale | Medium | Fixed |
| 5 | File-type detection | Silent fallback to extension-only detection when libmagic / mimetypes fail | Medium | Fixed (warn) |
| 6 | Path traversal | No `validate_output_path()` helper for future API endpoints | Low | Helper added |
| 7 | GH Actions | `google/clusterfuzzlite/actions/{build,run}_fuzzers@v1` pinned to mutable tag | **High** | Fixed (SHA pin) |
| 8 | GH Actions | `ByronWilliamsCPA/.github/.../python-qlty-coverage.yml@main` mutable ref | Medium | Fixed (SHA pin) |
| 9 | GH Actions | `ByronWilliamsCPA/.github/.../python-slsa.yml@main` mutable ref | Medium | Fixed (SHA pin) |
| 10 | GH Actions | `fips-compatibility.yml` missing `harden-runner` step | Low | Fixed |
| 11 | GH Actions | `release.yml` top-level `permissions: write-all` (broader than any single job needs) | Medium | Fixed (scoped to job) |
| 12 | GH Actions | `slsa-provenance.yml` top-level `permissions: contents: write` (build job doesn't need it) | Medium | Fixed (scoped to job) |
| 13 | GH Actions | No `dependabot.yml` (Renovate covers Python deps; nothing covered actions) | Low | Fixed (added) |
| F1 | PDF injection | "YAML injection via PDF metadata" | — | **False positive** (see below) |
| F2 | API | API server binds `0.0.0.0`, no auth | N/A | **No HTTP server exists** — deferred |
| F3 | Bug | `datetime.now()` used in `cli/main.py` without `from datetime import datetime` | Critical bug, not security | Out of scope (separate PR) |
| F4 | Storage | Extracted content written to plaintext files at user-chosen paths | By design | Documented, no change |

## Fixes applied

### 1. Unbounded read in dedup hash (High)

`src/data_ingestor/pipeline/router.py:181-188` previously did:

```python
with path.open("rb") as f:
    file_hash = hashlib.sha256(f.read()).hexdigest()
```

`max_file_size_mb` is 500 MB by default, so the dedup pre-check could
allocate half a gigabyte of resident memory per file just to compute a hash —
trivial denial-of-service on a batch run. Replaced with a 1 MiB streaming
loop. Same hash output, bounded memory.

### 2. PDF metadata sanitization (High)

`src/data_ingestor/parsers/pdf_parser.py:139-160` extracted PDF `/Info`
dictionary fields (`title`, `author`, `subject`, `keywords`, `creator`,
`producer`, dates) verbatim and handed them to the exporter, which serialized
them into JSON and YAML front matter. PDF metadata is attacker-controlled and
can contain:

- megabyte-sized strings (output bloat, downstream parser DoS),
- C0/C1 control bytes and NUL (corrupts text consumers, line-based loggers,
  some terminal renderers).

Added `PyMuPDFParser._sanitize_metadata_value`: strips ASCII control chars
(preserves `\t` and `\n`) and truncates each field to 1024 chars with an
explicit `...[truncated]` suffix.

> **Note on the "YAML injection" claim (F1).** The PDF/injection audit pass
> rated this CRITICAL because `yaml.dump(default_flow_style=False)` was
> claimed to fail to escape attacker-controlled YAML. Verified directly:
> PyYAML's `dump` quotes any value containing `---`, `&`, `*`, `:`, leading
> `?`, `!`, `|`, `>`, control chars, etc.; round-tripping malicious metadata
> through `dump` -> `safe_load` returns the original string unchanged. The
> finding as written is a false positive. The metadata length/control-char
> issue above is the real, reachable defense-in-depth concern, and is the one
> we fix.

### 3-4. Temp-file hardening (Medium)

- `src/data_ingestor/pipeline/pdf_analyzer.py:188` used
  `f"{stem}_upscaled_{int(time.time())}.pdf"`. One-second granularity makes
  concurrent runs collide and the path predictable on a multi-tenant host.
  Replaced with `uuid.uuid4().hex`.
- `src/data_ingestor/utils/pdf_upscaler.py:158-164` deleted the temp PNG
  inside the `with` block, so a `new_page.insert_image()` exception leaked the
  image to `/tmp`. Wrapped in `try/finally` with `Path.unlink(missing_ok=True)`.

### 5. Format-detector visibility (Medium)

`src/data_ingestor/utils/format_detector.py:96` falls through to
extension-only detection when both libmagic and `mimetypes` return no match.
This silently accepts an arbitrary file renamed `.pdf`. Behavior preserved
(don't want to break legitimate ingest in environments without libmagic), but
a `logger.warning` now fires every time the fallback is used so operators can
spot a misconfigured or stripped libmagic install.

### 6. `validate_output_path` helper (Low)

`src/data_ingestor/utils/path_validation.py` (new). Resolves a caller-supplied
output path against a base directory, fully resolving symlinks, and raises
`UnsafePathError` if the result is outside the base. Defeats `../` traversal
and symlink-pivot escapes.

The CLI does **not** call this — a local user typing `--output ../foo.json`
is making an authorized choice on their own filesystem. The helper exists so
that the planned FastAPI surface (`src/data_ingestor/api/` is currently
empty) can route every caller-supplied destination through it before opening
a file. Tests: `tests/unit/test_path_validation.py`.

### 7-9. GitHub Actions: SHA-pin the mutable refs (High / Medium)

Three workflows referenced actions by mutable refs (`@v1`, `@main`) — a
classic supply-chain footgun, since the owning org can republish those tags
to point at malicious commits. All three resolved via `git ls-remote` and
pinned, with the human-readable tag/branch preserved in a trailing comment:

| File | Before | After |
|------|--------|-------|
| `.github/workflows/cifuzzy.yml` | `google/clusterfuzzlite/actions/build_fuzzers@v1` | `@82652fb49e77bc29c35da1167bb286e93c6bcc05 # v1` |
| `.github/workflows/cifuzzy.yml` | `google/clusterfuzzlite/actions/run_fuzzers@v1` | `@82652fb49e77bc29c35da1167bb286e93c6bcc05 # v1` |
| `.github/workflows/coverage.yml` | `ByronWilliamsCPA/.github/.github/workflows/python-qlty-coverage.yml@main` | `@e067cdb7294f6221dbde74ef1f4c3ca735eed570 # main` |
| `.github/workflows/slsa-provenance.yml` | `ByronWilliamsCPA/.github/.github/workflows/python-slsa.yml@main` | `@e067cdb7294f6221dbde74ef1f4c3ca735eed570 # main` |

(Comment on the old workflow saying "cannot pin to SHA, maintained by Google"
was incorrect — `git ls-remote` resolves the `v1` tag fine.)

Also synced one stray `actions/setup-python@v5.3.0` SHA in
`slsa-provenance.yml` up to the v5.5.0 SHA used everywhere else.

### 10. Add `harden-runner` to `fips-compatibility.yml` (Low)

Every other workflow with direct steps starts with
`step-security/harden-runner@…` in `audit` mode. This one didn't. Added.
Reusable-workflow callers (`coverage.yml`, `sbom.yml`,
`python-compatibility.yml`) are intentionally not changed — they have no
direct steps; their callee workflows are responsible for runner hardening.

### 11-12. Least-privilege workflow permissions

- `release.yml` top-level was `contents: write / issues: write / pull-requests: write / id-token: write`. Only the `release` job actually needs those. Top-level reduced to `contents: read`; per-job block restored on the release job (with comments explaining why each scope is needed); `publish-pypi` already had its own per-job block.
- `slsa-provenance.yml` top-level was `contents: write / id-token: write / attestations: write`. The `build` job only needs `id-token: write` and `attestations: write` (for `actions/attest-build-provenance`); the `slsa` reusable-workflow call already declares its own permissions block. Top-level reduced to `contents: read`; per-job permissions added.

### 13. `dependabot.yml` (Low)

Added `.github/dependabot.yml` with weekly updates for `github-actions` and
`docker`. Python deps are covered by Renovate (`renovate.json` exists);
without this file, action SHAs and the Docker base image got no auto-update
coverage at all.

## Findings NOT fixed in this PR

### F1 — "YAML injection in PDF metadata" — false positive

Audit pass claimed `yaml.dump` was unsafe with attacker-controlled metadata.
Round-trip with malicious payloads (embedded `---`, anchors, multi-line) goes
through `safe_load` cleanly; PyYAML quotes everything. The real, reachable
concern is unbounded length / control bytes, which is fixed under finding 2.

### F2 — "API binds 0.0.0.0, no auth, no TLS" — premature

`src/data_ingestor/api/__init__.py` is an empty stub; no FastAPI app exists
and no `data-ingestor serve` command is wired up. `Dockerfile` and
`docker-compose.yml` reference `src.main:app`, which does not exist — the
container won't start. There is no live attack surface to harden. When the
API is actually built, it MUST:

1. Bind to `127.0.0.1` and front with a reverse proxy that terminates TLS,
   not `0.0.0.0` directly.
2. Require authentication on every endpoint (no `Depends(get_current_user)`
   dependency exists yet — `pyjwt` and `sqlalchemy` are installed but unused,
   suggesting an `AUTH-1` track is planned per `pyproject.toml`).
3. Route every output / staging path through `validate_output_path()` from
   finding 6.
4. Apply file-size limits BEFORE reading uploads (`max_file_size_mb` is
   defined but only checked in `base.py:90` after `path.stat()`, not on
   streaming uploads).

These belong in the PR that introduces the server, not this one.

### F3 — Missing `datetime` import in `cli/main.py` — functional bug, not security

The file-processing audit caught that `cli/main.py` references
`datetime.now()` at lines 573, 681, 702, 715, 847, 869, 1003 without ever
importing `datetime`. The `benchmark-configs`, `baseline-create`, and
`compare-configs` subcommands will `NameError` at runtime. This is a CLI
defect, not a security vulnerability — out of scope for a security PR. Flagged
here so it gets opened separately.

### F4 — Plaintext storage of extracted content — by design for a local CLI

Audit flagged that extracted document content is written to JSON/Markdown
without encryption-at-rest and without `0o600` permission hardening. For a
local CLI run by a single user against their own filesystem, this is the
expected behavior — the user chose the output path. Encryption-at-rest and
per-tenant isolation become real concerns the moment this runs as a shared
service (see F2); they should be designed in then, not bolted on now.

### CLI output-path traversal (audit issues 1.1–1.4) — accepted

CLI is a local-user tool; `--output ../foo.json` is the user authorizing a
write to their own path. Helper added (finding 6) so any future API surface
can confine writes. Not enforced on the CLI to avoid breaking existing
operator scripts that rely on relative output paths.

## What was checked and came back clean

- **Subprocess / shell exec**: no `subprocess`, `os.system`, `shell=True`,
  `eval`, or `exec` against any PDF-derived data.
- **Insecure deserialization**: no `pickle.load`, no `yaml.load` without
  `SafeLoader`; benchmarking uses `yaml.safe_load` consistently.
- **Hardcoded credentials**: none. `OPENROUTER_API_KEY` is the only secret and
  is loaded via `os.getenv` (`src/data_ingestor/parsers/pdf_parser.py`). The
  config dict it ends up in is passed to the Marker library but is not logged
  anywhere I traced.
- **Archive extraction**: no `zipfile`, `tarfile`, `extractall` anywhere — no
  zip-slip or decompression-bomb surface to harden.
- **Workflow injection**: no `run:` step interpolates
  `${{ github.event.* }}` user-controlled fields directly into shell;
  `fips-compatibility.yml` correctly passes `workflow_dispatch` input through
  an env var.
- **`pull_request_target`**: not used by any workflow.
