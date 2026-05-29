# .github Folder Setup Requirements for data_ingestor

> Comprehensive analysis of .github configurations from reference projects and organization-level repository

**Date:** 2025-11-03
**Project:** data_ingestor - Enhanced PDF/Document Parsing System
**Analysis Source:**
- `/home/byron/dev/xero_crypto/.github/`
- `/home/byron/dev/PromptCraft/.github/`
- `https://github.com/williaby/.github` (org-level)

---

## Executive Summary

The data_ingestor project currently has an empty .github folder and needs a complete GitHub infrastructure setup. Based on analysis of two reference projects and the organization-level repository, this document outlines all required files and configurations.

### Required Components

1. **Root-Level Files** (6 files)
   - CODEOWNERS
   - PULL_REQUEST_TEMPLATE.md
   - security-exceptions.yml
   - Community health files (inherited or override)

2. **Workflow Files** (6+ workflows)
   - ci.yml - Main CI pipeline
   - pr-validation.yml - Dependency and standards validation
   - security-analysis.yml - Comprehensive security scanning
   - dependency-review.yml - PR dependency scanning
   - codeql.yml - Static code analysis
   - scorecard.yml - OpenSSF security scoring

3. **Optional Advanced Workflows**
   - renovate-auto-merge.yml - Automated dependency updates
   - nightly-isolation-monitoring.yml - Production monitoring

---

## Detailed File Analysis

### 1. CODEOWNERS

**Purpose:** Automated review assignment and branch protection enforcement

**Pattern from xero_crypto:**
```
# Global ownership
* @Byron

# Critical components
/src/data_ingestor/ @Byron
/src/parsers/ @Byron
/src/chunking/ @Byron
/src/export/ @Byron

# Configuration and deployment
/.github/ @Byron
/pyproject.toml @Byron
/uv.lock @Byron
/requirements*.txt @Byron

# Security-sensitive
/scripts/ @Byron
/.env* @Byron

# Documentation
/docs/ @Byron
README.md @Byron
CLAUDE.md @Byron
```

**data_ingestor Adaptation:**
- Replace crypto-specific paths with parsing/chunking paths
- Add `/src/parsers/` - Critical for PDF/document processing
- Add `/src/quality/` - Quality validation components
- Keep standard configuration file patterns

---

### 2. PULL_REQUEST_TEMPLATE.md

**Purpose:** Structured PR reviews with domain-specific sections

**Key Sections Needed:**

#### From xero_crypto (Financial Impact):
```markdown
## 📋 Change Summary
### Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation
- [ ] Security enhancement
- [ ] Performance improvement

### Description
<!-- Clear description -->

### Related Issues
<!-- Fixes #123 -->
```

#### data_ingestor Specific Additions:
```markdown
## 📄 Document Processing Impact

**Does this PR affect document parsing or quality validation?**
- [ ] Yes - Parser logic changes (requires testing)
- [ ] No - Non-parser changes only

**Affected Components:**
- [ ] PDF parser (Docling/Marker integration)
- [ ] Chunking strategies (by-title, token-based)
- [ ] Quality validation and scoring
- [ ] Export functionality
- [ ] OCR/Vision models
- [ ] Metadata extraction
```

#### From PromptCraft (Testing & Security):
```markdown
## 🧪 Testing Checklist
- [ ] All existing tests pass
- [ ] New tests added for new functionality
- [ ] Integration tests updated
- [ ] Security tests pass

## 🔒 Security Considerations
- [ ] No hardcoded secrets or credentials
- [ ] Input validation implemented
- [ ] Error messages don't leak sensitive data
- [ ] Logging excludes sensitive information
```

#### Dependency Management Section:
```markdown
## 📦 Dependency Updates (if applicable)

### Security Assessment
- [ ] No known vulnerabilities in updated dependencies
- [ ] Requirements.txt updated
- [ ] uv.lock synchronized

### Auto-merge Criteria
- [ ] All CI checks pass
- [ ] Test coverage maintained ≥80%
- [ ] Only patch/minor updates
```

---

### 3. security-exceptions.yml

**Purpose:** Centralized registry for approved security scan exceptions

**Structure from xero_crypto:**
```yaml
version: "1.0"
metadata:
  description: "Security exceptions for data_ingestor document parsing system"
  last_reviewed: "2025-11-03"
  next_review: "2026-02-03"
  project: "data-ingestor"
  criticality: "medium"  # Document processing

exceptions:
  - id: "EX-001"
    type: "false-positive"
    tool: "bandit"
    rule: "B101"  # assert_used
    file: "tests/"
    line: "*"
    justification: "Test assertions are standard practice"
    risk_accepted: true
    expires: "2026-06-01"
    approved_by: "@Byron"
    approved_date: "2025-11-03"
    pr_reference: "Initial setup"
    mitigation: "Assertions only in test code, not production"
```

**data_ingestor Specific Exceptions:**
- Document processing temp directories
- PDF parsing library dependencies
- Vision model dependencies (transformers, torch)
- OCR library patterns

---

### 4. CI Workflow (ci.yml)

**Purpose:** Main continuous integration pipeline

**Key Features from Both Projects:**

#### Setup Phase (from PromptCraft):
```yaml
env:
  CI_ENVIRONMENT: true
  UV_VERSION: 0.5.0
  UV_CACHE_DIR: ~/.cache/uv
  UV_PROJECT_ENVIRONMENT: .venv
  MYPY_CACHE_DIR: ~/.cache/mypy

jobs:
  setup-optimized:
    name: Enhanced Setup
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - name: Install uv and Configure
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Cache uv dependencies
        uses: actions/cache@v4
```

#### Test Phase (adapted from xero_crypto):
```yaml
  test:
    name: Test Suite (Python ${{ matrix.python-version }})
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    steps:
      - name: Run test suite
        run: |
          uv run pytest -v \
            --cov=src \
            --cov-report=xml:coverage.xml \
            --cov-report=term-missing \
            --cov-report=html:htmlcov \
            --junitxml=junit.xml \
            -m "not slow" \
            tests/
```

#### Quality Checks (from both):
```yaml
  quality-checks:
    steps:
      - name: Type checking with MyPy
        run: uv run mypy src --config-file=pyproject.toml
      - name: Code formatting
        run: uv run black . --check
      - name: Linting
        run: uv run ruff check .
      - name: Security scanning
        run: |
          uv run bandit -r src
          uv run safety check
```

**data_ingestor Specific:**
- No database services needed (unlike xero_crypto)
- Test data fixtures for PDF documents
- Vision model dependency validation
- OCR library availability checks

---

### 5. PR Validation Workflow (pr-validation.yml)

**Purpose:** Dependency consistency and standards compliance

**From xero_crypto Pattern:**
```yaml
name: PR Validation

on:
  pull_request:
    branches:
      - main
      - develop

jobs:
  validate-dependencies:
    steps:
      - name: Check dependency changes
        run: |
          if git diff --name-only origin/${{ github.event.pull_request.base.ref }}...HEAD | grep -E "(uv\.lock|pyproject\.toml)"; then
            echo "changed=true"
          fi

      - name: Validate Requirements Sync
        if: dependencies changed
        run: |
          uv export --format requirements-txt --no-hashes --output requirements.txt
          if ! git diff --exit-code requirements*.txt; then
            echo "::error::Requirements files out of sync"
            exit 1
          fi
```

**data_ingestor Project Structure Validation:**
```yaml
      - name: Validate Project Structure
        run: |
          required_dirs=(
            "src/data_ingestor"
            "src/data_ingestor/parsers"
            "src/data_ingestor/chunking"
            "src/data_ingestor/quality"
            "src/data_ingestor/export"
            "tests"
            "docs"
          )

          required_files=(
            "pyproject.toml"
            "README.md"
            "CLAUDE.md"
            ".env.example"
          )
```

---

### 6. Security Analysis Workflow (security-analysis.yml)

**Purpose:** Comprehensive security scanning for document processing system

**From xero_crypto (Enhanced for Financial Systems):**
```yaml
name: Security Analysis

on:
  pull_request:
    paths:
      - '**/*.py'
      - '.github/workflows/security-analysis.yml'
      - 'pyproject.toml'
  schedule:
    - cron: '30 2 * * 1'  # Weekly Monday 2:30 AM UTC
  workflow_dispatch:

permissions:
  security-events: write

jobs:
  codeql-analysis:
    uses: github/codeql-action/init@v3
    with:
      languages: python
      queries: security-extended,security-and-quality

  dependency-security:
    uses: actions/dependency-review-action@v4
    with:
      fail-on-severity: moderate
      license-check: true

  security-scanning:
    steps:
      - name: Bandit Security Analysis
        run: uv run bandit -r src -f json -o bandit-report.json

      - name: Safety Vulnerability Scan
        run: uv run safety check --json --output safety-report.json

      - name: Semgrep Security Analysis
        uses: semgrep/semgrep-action@v1
        with:
          config: p/security-audit
```

**data_ingestor Adaptations:**
- Focus on document processing libraries (docling, marker, transformers)
- Vision model security validation
- File upload/processing security patterns
- Temporary file handling validation

---

## Community Health Files

### Organization-Level Inheritance

The following files are inherited from `https://github.com/williaby/.github` and apply automatically unless overridden:

1. **CODE_OF_CONDUCT.md** - Community behavioral standards
2. **SECURITY.md** - Vulnerability reporting process
3. **CONTRIBUTING.md** - Contribution guidelines
4. **SUPPORT.md** - Support channels and SLA
5. **GOVERNANCE.md** - Project governance model
6. **FUNDING.yml** - Sponsorship information

### When to Override

Override organization-level files only when:
- Project has unique security requirements (e.g., financial data)
- Different contribution workflow needed
- Project-specific support channels

**Recommendation for data_ingestor:** Inherit all organization-level files. No overrides needed.

---

## Additional Workflows to Consider

### From PromptCraft (Advanced):

1. **dependency-review.yml** - Enhanced dependency scanning for PRs
2. **scorecard.yml** - OpenSSF security scorecard
3. **codeql.yml** - Dedicated CodeQL workflow (separate from security-analysis)
4. **renovate-auto-merge.yml** - Automated dependency PR merging

### From xero_crypto:

1. **nightly-isolation-monitoring.yml** - Production health monitoring
2. **test.yml** - Separate standalone test workflow

**Recommendation:** Start with core 3 workflows (ci, pr-validation, security-analysis), add advanced workflows as project matures.

---

## Implementation Priority

### Phase 1: Essential (Immediate)
1. CODEOWNERS
2. PULL_REQUEST_TEMPLATE.md
3. security-exceptions.yml
4. ci.yml

### Phase 2: Core Security (Week 1)
5. pr-validation.yml
6. security-analysis.yml

### Phase 3: Advanced (Month 1)
7. dependency-review.yml
8. codeql.yml
9. scorecard.yml

### Phase 4: Automation (As Needed)
10. renovate-auto-merge.yml
11. nightly-monitoring.yml (if production deployment planned)

---

## Key Differences from Reference Projects

### xero_crypto → data_ingestor

| Aspect | xero_crypto | data_ingestor |
|--------|-------------|---------------|
| **Focus** | Financial accounting, crypto reconciliation | Document parsing, quality validation |
| **Database** | PostgreSQL + Redis required | No database services needed |
| **Critical Paths** | `/src/reconciliation/`, `/src/chart_of_accounts/` | `/src/parsers/`, `/src/chunking/`, `/src/quality/` |
| **Dependencies** | Web3, psycopg2, sqlalchemy | docling, marker, transformers, torch |
| **Security Focus** | Financial data, private keys | File processing, temp files, vision models |
| **Test Markers** | `financial`, `reconciliation`, `precision` | `ocr`, `vision`, `quality`, `parsing` |

### PromptCraft → data_ingestor

| Aspect | PromptCraft | data_ingestor |
|--------|-------------|---------------|
| **Focus** | RAG system, LLM orchestration | Document parsing pipeline |
| **Services** | Qdrant, Redis | None required |
| **Complexity** | Multi-service architecture | Single-pipeline architecture |
| **Dependencies** | sentence-transformers, qdrant-client | docling, marker, pdfplumber |
| **Workflows** | 15+ workflows (deployment, docs, UI testing) | 3-6 core workflows |

---

## Environment Variables

### Required for CI/CD

```yaml
# From pyproject.toml and .env.example
CI_ENVIRONMENT: true
UV_VERSION: 0.5.0
UV_CACHE_DIR: ~/.cache/uv
UV_PROJECT_ENVIRONMENT: .venv
MYPY_CACHE_DIR: ~/.cache/mypy

# data_ingestor specific
DATA_INGESTOR_TEMP_DIR: /tmp/data_ingestor
DATA_INGESTOR_OUTPUT_DIR: ./output
```

### GitHub Secrets Needed

```
CODECOV_TOKEN - Coverage reporting (optional)
SEMGREP_APP_TOKEN - Semgrep security scanning (optional)
```

---

## Next Steps

1. **Review this document** with project owner
2. **Create Phase 1 files** (CODEOWNERS, PULL_REQUEST_TEMPLATE, security-exceptions, ci.yml)
3. **Test CI workflow** with test PR
4. **Iterate and refine** based on actual project needs
5. **Add Phase 2-3** workflows as project stabilizes

---

## References

- xero_crypto CI: Comprehensive financial system CI with database integration
- PromptCraft CI: Optimized uv caching and dependency management
- Organization .github: Community health files and standards
- GitHub Actions Best Practices: https://docs.github.com/en/actions/learn-github-actions/best-practices
