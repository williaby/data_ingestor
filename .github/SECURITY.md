# Security Policy

## Supported Versions

We currently support the following versions with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

**Please DO NOT report security vulnerabilities through public GitHub issues.**

### Private Disclosure Process

We take security seriously and appreciate responsible disclosure. To report a security vulnerability:

1. **Email**: Send details to byronawilliams@gmail.com
2. **Include**:
   - Description of the vulnerability
   - Steps to reproduce the issue
   - Potential impact assessment
   - Suggested fix (if available)
   - Your contact information for follow-up

### What to Expect

| Timeline | Action |
|----------|--------|
| **< 48 hours** | Initial acknowledgment of your report |
| **< 7 days** | Detailed status update and validation results |
| **Varies by severity** | Fix development and deployment timeline |

### Severity-Based Response Timeline

- **Critical** (Remote code execution, data breach): 24-48 hours
- **High** (Authentication bypass, privilege escalation): 7 days
- **Medium** (Information disclosure, DoS): 30 days
- **Low** (Minor information leakage): 90 days

## Security Update Process

Our security response follows this workflow:

1. **Validation**: Verify and assess the reported vulnerability
2. **Development**: Create fix in a private security branch
3. **Advisory**: Prepare GitHub Security Advisory
4. **Coordination**: Coordinate disclosure timeline with reporter
5. **Release**: Deploy fix and publish advisory
6. **CVE**: Request CVE assignment for significant vulnerabilities

## Security Best Practices for Users

When using Data Ingestor, we recommend:

- ✅ Keep dependencies up to date (use Renovate/Dependabot)
- ✅ Use the latest stable release version
- ✅ Enable security scanning in your CI/CD pipeline
- ✅ Validate all document inputs (especially untrusted PDFs)
- ✅ Run in sandboxed environments for untrusted content
- ✅ Monitor for security advisories
- ✅ Review our [CHANGELOG](CHANGELOG.md) for security fixes

## Document Processing Security Considerations

**Data Ingestor processes potentially untrusted documents.** Please be aware:

### Input Validation
- All file paths are sanitized to prevent directory traversal
- MIME type validation prevents format confusion attacks
- File size limits prevent resource exhaustion

### Parser Security
- PDF parsers may be vulnerable to malformed documents
- OCR processing can be resource-intensive (potential DoS)
- External content extraction is disabled by default

### Recommended Security Controls
```python
from data_ingestor.core.config import Settings

settings = Settings(
    max_file_size_mb=100,  # Limit file sizes
    enable_ocr=False,      # Disable OCR for untrusted content
    validate_strict=True,   # Strict validation mode
)
```

## Known Security Considerations

### PDF Processing (marker-pdf)
- **License**: GPL-3.0 (be aware of licensing implications)
- **CVE-2025-78558**: ReDoS vulnerability in constrained regex dependency
  - Mitigation: Input validation on regex patterns
  - Trade-off: Advanced PDF features vs vulnerability exposure
  - For production: Consider skipping `--with advanced-pdf` group

### Dependency Security
- We use multiple security scanning tools:
  - **Safety**: Python dependency vulnerability scanning
  - **Bandit**: Python code security analysis
  - **CodeQL**: Semantic code analysis
  - **Semgrep**: Pattern-based security checks
  - **Trivy**: Container and dependency scanning
  - **Snyk**: Real-time vulnerability monitoring

## Security Scanning Schedule

- **On every PR**: CodeQL, Bandit, Safety checks
- **Weekly**: Comprehensive security analysis, dependency audits
- **On dependency updates**: Automated vulnerability scanning

## Additional Resources

- [Organization Security Policy](https://github.com/williaby/.github/blob/main/SECURITY.md)
- [Code of Conduct](https://github.com/williaby/.github/blob/main/CODE_OF_CONDUCT.md)
- [OpenSSF Scorecard](https://scorecard.dev/viewer/?uri=github.com/Byron/data_ingestor)

## Security Contact

- **Primary**: byronawilliams@gmail.com
- **Organization Security**: [williaby org security team](https://github.com/williaby)

## Acknowledgments

We appreciate security researchers who responsibly disclose vulnerabilities. Contributors will be acknowledged in our security advisories (with permission).

---

**Last Updated**: 2025-11-05
**Policy Version**: 1.0
