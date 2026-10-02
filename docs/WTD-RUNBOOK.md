# WTD (What The Diff) Runbook

> **Purpose**: Reference guide for using What The Diff AI-powered PR summaries in the Data Ingestor project
>
> **Last Updated**: 2025-11-06
> **Maintained By**: Development Team

## Overview

What The Diff (WTD) is an AI-powered service that automatically generates comprehensive summaries of pull request changes. It helps reviewers quickly understand what changed and why, improving code review efficiency and team collaboration.

### Key Features

- **Automated PR Summaries**: AI-generated explanations of code changes inserted directly into PR descriptions
- **Smart Filtering**: Excludes large datasets, generated files, and build artifacts to conserve tokens
- **Shortcode Integration**: Use `wtd:summary`, `wtd:joke`, or `wtd:poem` placeholders in PR templates
- **Manual Trigger**: Add the WTD label to any PR to generate summaries on demand

## Account Setup

### Prerequisites

1. **GitHub Account**: WTD integrates via GitHub OAuth
2. **Repository Access**: Admin or write access to enable WTD for this repository
3. **Token Budget**: Default 50,000 tokens per PR (typical usage: 2,000-8,000 tokens)

### Initial Setup

1. Visit [whatthediff.ai](https://whatthediff.ai/)
2. Click "Sign in with GitHub"
3. Authorize What The Diff to access your repositories
4. Navigate to your dashboard
5. Enable the `data_ingestor` repository
6. Configure repository-specific settings (see Configuration section)

## Configuration

### Trigger Conditions

WTD activates automatically when:
- Pull requests are **opened**
- Pull requests are **reopened**
- New commits are **pushed** to an open PR
- The **WTD label** is manually added to a PR

**Bot Exclusion**: WTD skips contributions from bot accounts (usernames ending in `[bot]`)

### Shortcode Usage (Recommended)

Add shortcodes to your PR description template:

```markdown
## Summary
wtd:summary

## Changes
<!-- Detailed change description -->

---
wtd:joke
```

**Available Shortcodes**:
- `wtd:summary` - Comprehensive explanation of what changed and why
- `wtd:joke` - Developer-themed humor about the changes
- `wtd:poem` - Poetic interpretation of your changes

### Token Limits

- **Default**: 50,000 tokens per PR
- **Typical Usage**: 2,000-8,000 tokens
- **Large PRs**: May require manual token limit adjustment in dashboard

### File Exclusion Strategy

WTD intelligently excludes files that don't provide meaningful review value. This project's exclusions are managed through `.gitattributes` configuration.

**Excluded Categories**:

1. **Benchmark Datasets** (large, static data files)
   - `data/benchmarks/`
   - `data/readoc/`
   - `data/doclaynet/`
   - `data/pubtables/`
   - `data/wind_docs/`

2. **Generated Reports and Results**
   - `test_output/`
   - `test_results/`
   - `results/`
   - `benchmark_results/`
   - `evaluation_results/`
   - `reports/*.html`, `reports/*.csv`, `reports/*.json`

3. **Build Artifacts and Distribution**
   - `dist/`
   - `build/`
   - `htmlcov/`

4. **Lock Files and Dependencies**
   - `uv.lock`
   - `package-lock.json`

5. **Temporary and Cache Files**
   - `tmp_cleanup/`
   - `__pycache__/`
   - `.pytest_cache/`
   - `.mypy_cache/`
   - `.ruff_cache/`
   - `.benchmark_cache/`

6. **Coverage and Security Reports**
   - `coverage.json`
   - `coverage.xml`
   - `bandit-report.json`

7. **Generated Analysis Documents**
   - `*_ANALYSIS.md`
   - `*_REVIEW.md`
   - `*_PROGRESS.md`

8. **Log Files**
   - `*.log`
   - `test_output.txt`

## Advanced Configuration

### File Exclusion Overrides

**Dashboard Settings** (via whatthediff.ai):
- **File Exclusion**: Add patterns to exclude specific files (e.g., `*.min.js`, `*.generated.py`)
- **File Inclusion**: Override exclusions by specifying directories to include only
- **Branch Filtering**: Ignore specific branches using wildcards (e.g., `dependabot/*`)
- **PR Title Filtering**: Skip PRs matching specific title patterns

### Branch Strategy

**Recommended Exclusions**:
- `dependabot/*` - Automated dependency updates
- `renovate/*` - Automated maintenance PRs
- `release/*` - Release preparation branches (may want summaries)

### Notification Integration

**Available Integrations**:
1. **Slack**: Send PR summaries to team channels
2. **Webhooks**: Custom integration endpoints
3. **Email**: Weekly consolidated reports
4. **Multiple Languages**: Configure summary language per team member

## PR Preparation Workflow

### Standard Workflow (Automated)

```bash
# 1. Create feature branch
git checkout -b feature/add-docling-parser

# 2. Make changes and commit
git add .
git commit -m "feat: add Docling parser for Office format support"

# 3. Push to remote
git push -u origin feature/add-docling-parser

# 4. Create PR with shortcodes in description
gh pr create --title "feat: add Docling parser for Office format support" \
  --body "$(cat <<'EOF'
## Summary
wtd:summary

## Changes
- Add Docling parser integration for DOCX, XLSX, PPTX
- Implement TableFormer model for 97.9% table accuracy
- Add MIT-licensed parser fallback option

## Test Plan
- [ ] Unit tests for Docling parser
- [ ] Integration tests with sample Office files
- [ ] Benchmark against existing parsers

---
wtd:joke
EOF
)"
```

### Manual Trigger

For existing PRs without shortcodes:
1. Add the **WTD label** to the PR
2. WTD generates a comment with the summary
3. Review and incorporate summary into PR description

### Integration with `mcp__zen-core__pr_prepare`

The project uses the automated PR preparation workflow from MCP Server. To integrate WTD:

1. **Include Shortcode by Default**: Add `--include-wtd` flag (default: true)
2. **Force WTD for Large PRs**: Use `--force-wtd` to override size restrictions
3. **Skip WTD**: Use `--no-wtd` to skip shortcode inclusion

**Example**:
```bash
# PR preparation with WTD (automatic)
mcp__zen-core__pr_prepare --target-branch main --change-type feat

# Skip WTD for small changes
mcp__zen-core__pr_prepare --target-branch main --change-type docs --no-wtd

# Force WTD for large refactoring
mcp__zen-core__pr_prepare --target-branch main --change-type refactor --force-wtd
```

## Usage Patterns

### When to Use WTD

**Recommended**:
- Feature implementations (>100 lines changed)
- Complex refactorings
- Multi-file architectural changes
- Cross-component integrations
- Performance optimizations
- Security enhancements

**Optional**:
- Small bug fixes (<50 lines)
- Documentation updates
- Configuration changes
- Dependency updates

**Skip**:
- Automated bot PRs (dependabot, renovate)
- WIP/draft PRs (add label when ready for review)
- Trivial typo fixes

### Best Practices

1. **Write Descriptive Commits**: WTD analyzes commit messages - use conventional commits
2. **Use Shortcodes Early**: Add `wtd:summary` to PR template before opening
3. **Review AI Output**: Validate generated summaries for accuracy
4. **Supplement with Context**: Add project-specific context AI might miss
5. **Monitor Token Usage**: Check dashboard for usage patterns and adjust exclusions

### Common Workflows

#### Feature Development
```markdown
## Summary
wtd:summary

## Motivation
<!-- Why is this change needed? Business context? -->

## Implementation Details
<!-- Technical approach, design decisions, trade-offs -->

## Testing
<!-- Test strategy, coverage, edge cases -->

## Documentation
<!-- README updates, API docs, runbooks -->

---
wtd:joke
```

#### Bug Fix
```markdown
## Summary
wtd:summary

## Bug Description
<!-- What was broken? How did it manifest? -->

## Root Cause
<!-- Why did the bug occur? -->

## Fix Approach
<!-- How does this fix address the root cause? -->

## Regression Prevention
<!-- Tests added to prevent reoccurrence -->
```

#### Refactoring
```markdown
## Summary
wtd:summary

## Refactoring Goals
<!-- What are we improving? Why now? -->

## Changes
<!-- What patterns changed? Architecture shifts? -->

## Migration Path
<!-- How to adopt new patterns? Deprecation timeline? -->

## Validation
<!-- How do we know behavior is unchanged? -->

---
wtd:poem
```

## Monitoring and Maintenance

### Token Usage Monitoring

**Dashboard Metrics**:
- Total tokens consumed per repository
- Average tokens per PR
- Token consumption trends
- Most expensive PRs (identify exclusion gaps)

**Optimization Strategies**:
1. Review high-token PRs to identify missing exclusions
2. Add `.gitattributes` patterns for new generated file types
3. Adjust branch/title filters to skip automated PRs
4. Configure per-PR token limits for different change types

### Quality Validation

**Review Checklist**:
- [ ] Summary accurately describes changes
- [ ] No sensitive information exposed
- [ ] Technical terminology correct
- [ ] Tone appropriate for team culture
- [ ] No hallucinated features or behavior

**Feedback Loop**:
1. Report inaccuracies via [email protected]
2. Update PR description with corrections
3. Document common AI misunderstandings
4. Adjust commit message patterns for clarity

### `.gitattributes` Maintenance

**Review Trigger Events**:
- New benchmark datasets added
- New code generation tools introduced
- New build/distribution directories
- New testing frameworks with generated reports
- Repository structure changes

**Update Process**:
```bash
# 1. Edit .gitattributes with new patterns
vim .gitattributes

# 2. Commit changes
git add .gitattributes
git commit -m "chore: update WTD exclusions for new benchmark data"

# 3. Validate on next PR
# Check WTD summary to ensure excluded files not analyzed
```

## Troubleshooting

### WTD Not Generating Summaries

**Checklist**:
1. Is repository enabled in WTD dashboard?
2. Is PR author a bot account (auto-skipped)?
3. Are there enough file changes to analyze?
4. Has token limit been exceeded?
5. Is PR targeting excluded branch?

**Solution**:
- Check dashboard configuration
- Manually add WTD label to trigger
- Review token usage and adjust limits
- Verify branch/title filters

### Incorrect or Incomplete Summaries

**Common Causes**:
1. Poor commit messages (WTD analyzes commits + diffs)
2. Large PRs exceeding context window
3. Missing project-specific context
4. Complex architectural changes

**Solutions**:
- Improve commit message quality (conventional commits)
- Split large PRs into smaller logical chunks
- Add PR description context before WTD runs
- Supplement AI summary with human explanation

### Token Budget Exhausted

**Symptoms**:
- Summaries cut off mid-sentence
- "Token limit exceeded" warnings
- Partial analysis of large PRs

**Solutions**:
1. **Increase Limit**: Adjust per-PR token limit in dashboard
2. **Add Exclusions**: Review high-token PRs for missing `.gitattributes` patterns
3. **Split PR**: Break large changes into smaller, focused PRs
4. **Manual Summary**: For rare large refactorings, write summary manually

### Sensitive Information Exposure

**Prevention**:
- Never include secrets, API keys, or credentials in commits
- Use `.gitattributes` to exclude configuration files with sensitive data
- Review WTD summaries before merging PR
- Enable GitHub secret scanning

**Response**:
1. Immediately revoke exposed credentials
2. Remove sensitive information from commit history
3. Update `.gitattributes` to exclude file types
4. Report to [email protected]

## Integration with Development Standards

### Response-Aware Development (RAD)

WTD complements RAD assumption tagging:
- **AI Summary**: High-level change explanation
- **Assumption Tags**: Low-level invariants and edge cases

**Example**:
```python
# WTD explains: "Adds OCR pre-flight analysis for intelligent routing"
# RAD tags critical assumptions:
# #CRITICAL: ocr: Assumes OCR parser available in registry
# #VERIFY: Must validate parser registration before routing
def preflight_analysis(document: Document) -> OCRStrategy:
    # Implementation...
```

### Pre-Commit Integration

WTD runs **after** pre-commit hooks:
1. Pre-commit: Black, Ruff, MyPy, Markdownlint, Yamllint, Security scans
2. Git push: Commits pushed to remote
3. PR creation: GitHub PR opened with `wtd:summary` shortcode
4. WTD analysis: AI generates summary from commits + diffs
5. Review: Human validates AI summary + assumption tags

### Claude Code Supervisor Workflow

WTD integrates with supervisor task tracking:
1. **TodoWrite**: Track feature implementation
2. **Agent Assignment**: Specialized agents complete tasks
3. **Agent Validation**: Supervisor reviews agent work
4. **PR Preparation**: `mcp__zen-core__pr_prepare` with WTD integration
5. **WTD Analysis**: AI summarizes cumulative changes from todo list
6. **Final Review**: Supervisor validates WTD summary against todo completion

## References

- [What The Diff Official Documentation](https://whatthediff.ai/docs)
- [Getting Started Guide](https://whatthediff.ai/getting-started)
- [GitHub Integration Guide](https://whatthediff.ai/github)
- [Support Contact](mailto:[email protected])

## Appendix

### Example `.gitattributes` Configuration

See [.gitattributes](.gitattributes) in repository root for complete configuration.

### Token Consumption Benchmarks

**Typical Token Usage** (Data Ingestor Project):

| PR Type | Files Changed | Lines Changed | Token Usage | Notes |
|---------|---------------|---------------|-------------|-------|
| Bug Fix | 1-3 | 10-50 | 500-1,500 | Single component |
| Feature | 5-15 | 100-500 | 2,000-5,000 | Multi-component |
| Refactor | 10-30 | 500-2,000 | 5,000-15,000 | Architectural |
| Integration | 20-50 | 1,000-5,000 | 10,000-30,000 | Cross-cutting |

**Optimization Impact**:
- **Without Exclusions**: ~20,000 tokens (includes benchmark data, reports)
- **With Exclusions**: ~3,000 tokens (75% reduction)

### Change Log

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2025-11-06 | 1.0.0 | Initial WTD runbook for Data Ingestor | Development Team |

---

**Maintained By**: Development Team
**Review Cadence**: Quarterly or when repository structure changes significantly
**Next Review**: 2025-14-06
