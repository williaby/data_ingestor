# ADR-001: Consolidate Python Linting with Ruff

**Status**: ✅ **Accepted**
**Date**: 2025-11-17
**Deciders**: Byron Williams
**Tags**: tooling, linting, ruff, consolidation

## Context

The Data Ingestor project uses multiple overlapping Python linting and formatting tools:

- **Black**: Code formatting (line length, quotes, indentation)
- **Ruff**: Linting (multiple rule categories)
- **MyPy**: Type checking (strict mode)
- **Bandit**: Security scanning
- **interrogate**: Docstring coverage metrics

### Problems

1. **Tool Duplication**: Black and Ruff formatter serve similar purposes
2. **Performance Overhead**: Multiple tools running sequentially in pre-commit hooks
3. **Configuration Fragmentation**: Settings spread across multiple tool configurations
4. **Maintenance Burden**: Keeping multiple tools updated and coordinated

### Requirements

- Maintain comprehensive code quality coverage for document processing code
- Preserve Google-style docstring enforcement
- Keep security scanning capabilities for file handling operations
- Maintain strict type checking for data models and parsers
- Minimize pre-commit hook execution time for developer productivity

## Decision

**Consolidate Black and extend Ruff to handle formatting, linting, and basic security checks.**

### Changes

1. **Replace Black with Ruff Format**
   - Enable `[tool.ruff.format]` in pyproject.toml
   - Black-compatible formatting (88 char line length)
   - Add `ruff-format` pre-commit hook

2. **Configure Ruff for Document Processing**
   - Add rule categories: D (pydocstyle), S (security), N (naming), A (builtins)
   - Google-style docstring convention for parser documentation
   - File-handling security rules (path traversal, unsafe file operations)

3. **Keep Specialized Tools**
   - **MyPy**: Unique type checking for Pydantic models and parser interfaces
   - **interrogate**: Docstring coverage metrics for API documentation
   - **Bandit**: Advanced security pattern detection for document processing

### Configuration

```toml
[tool.ruff]
line-length = 88
target-version = "py311"

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "B",    # flake8-bugbear
    "D",    # pydocstyle
    "S",    # flake8-bandit (security)
    "N",    # pep8-naming
    "UP",   # pyupgrade
]

[tool.ruff.lint.pydocstyle]
convention = "google"
```

## Consequences

### Positive

1. **Performance**: Pre-commit hooks ~3-5x faster (Ruff is written in Rust)
2. **Simplicity**: Single tool for formatting + linting reduces configuration complexity
3. **Consistency**: Unified code style across document processing modules
4. **Maintenance**: Fewer tools to update and maintain
5. **Developer Experience**: Faster feedback loop in pre-commit hooks

### Negative

1. **Migration Effort**: Need to update all existing code to pass Ruff checks
2. **Learning Curve**: Developers need to learn Ruff-specific rule codes
3. **Maturity**: Ruff is newer than Black (though widely adopted)
4. **Partial Security**: Ruff S rules don't replace full Bandit scanning

### Mitigation

- Keep Bandit in security-analysis.yml workflow for deep security scanning
- Document Ruff rule codes in CLAUDE.md for developer reference
- Gradual migration: Add rules incrementally to avoid overwhelming developers
- Pre-commit hooks provide immediate feedback before push

## Related Decisions

- ADR-002: GitHub Actions Security Hardening
- ADR-003: Poetry Dependency Management

## References

- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Ruff vs Black Performance](https://github.com/astral-sh/ruff#how-does-ruff-compare-to-black)
- [Pre-commit Hook Integration](https://pre-commit.com/)
