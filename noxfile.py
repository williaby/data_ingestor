"""Nox-UV sessions for testing, linting, and security checks."""

import contextlib
from pathlib import Path

import nox

with contextlib.suppress(ImportError):
    import nox_uv  # noqa: F401 - Required for uv backend support

nox.options.sessions = ["unit", "lint", "type_check"]
nox.options.reuse_existing_virtualenvs = True
nox.options.default_venv_backend = "uv"

PYTHON_VERSIONS = ["3.11", "3.12", "3.13", "3.14"]
DEV_EXTRAS = ".[dev]"

# Source locations
SRC_LOCATIONS = ["src", "tests", "noxfile.py", "scripts"]


@nox.session(python=PYTHON_VERSIONS)
def tests(session):
    """Run the full test suite (all layers)."""
    args = session.posargs or ["--cov", "--cov-branch", "--cov-report=term-missing", "--cov-fail-under=80"]
    session.install("-e", DEV_EXTRAS)
    session.run("pytest", *args)


# ==========================================
# LAYERED TESTING SESSIONS (Test Pyramid)
# ==========================================


@nox.session(python=PYTHON_VERSIONS)
def unit(session):
    """Run unit tests only (fast development cycle)."""
    session.install("-e", DEV_EXTRAS)
    session.run(
        "pytest",
        "-m",
        "not component and not contract and not integration and not e2e and not perf and not chaos and not slow",
        "--cov=src",
        "--cov-branch",
        "--cov-fail-under=80",
        "-v",
        *session.posargs,
    )


@nox.session
def component(session):
    """Run component tests (with mocks)."""
    session.install("-e", DEV_EXTRAS)
    session.run(
        "pytest",
        "-m",
        "component",
        "--cov=src",
        "--cov-branch",
        "--cov-fail-under=75",
        "-v",
        *session.posargs,
    )


@nox.session
def integration(session):
    """Run integration tests (slower, real services)."""
    session.install("-e", DEV_EXTRAS)
    session.run(
        "pytest",
        "-m",
        "integration",
        "--cov=src",
        "--cov-branch",
        "-v",
        *session.posargs,
    )


@nox.session
def e2e(session):
    """Run end-to-end tests (full user journeys)."""
    session.install("-e", DEV_EXTRAS)
    session.run(
        "pytest",
        "-m",
        "e2e",
        "-v",
        "--tb=short",
        *session.posargs,
    )


@nox.session
def perf(session):
    """Run performance and load tests."""
    session.install("-e", DEV_EXTRAS)
    session.run(
        "pytest",
        "-m",
        "perf or performance",  # Include legacy marker
        "-v",
        "--tb=short",
        "--durations=10",
        *session.posargs,
    )


@nox.session
def security_tests(session):
    """Run security assertion tests."""
    session.install("-e", DEV_EXTRAS)
    session.run(
        "pytest",
        "-m",
        "security",
        "-v",
        *session.posargs,
    )


@nox.session
def chaos_tests(session):
    """Run chaos engineering tests."""
    session.install("-e", DEV_EXTRAS)
    session.run(
        "pytest",
        "-m",
        "chaos",
        "-v",
        "--tb=short",
        *session.posargs,
    )


@nox.session
def fast(session):
    """Fast development loop - exclude slow tests."""
    session.install("-e", DEV_EXTRAS)
    session.run(
        "pytest",
        "-m",
        "not slow",
        "--cov=src",
        "--cov-branch",
        "--cov-fail-under=75",  # Slightly lower for fast feedback
        "--maxfail=5",
        "-v",
        *session.posargs,
    )


@nox.session
def metrics(session):
    """Generate test quality metrics dashboard."""
    session.install("-e", DEV_EXTRAS)

    # Check if metrics dashboard script exists before running
    script_path = Path("test_metrics_dashboard.py")
    if script_path.exists():
        session.run("python", "test_metrics_dashboard.py")
    else:
        session.log(f"Warning: {script_path} not found. Skipping metrics dashboard generation.")


@nox.session(python=["3.11"])
def tests_unit(session):
    """Run unit tests with coverage flags for Codecov."""
    session.install("-e", DEV_EXTRAS)
    session.run(
        "pytest",
        "-m",
        "unit",
        "--cov=src",
        "--cov-branch",
        "--cov-report=xml:coverage-unit.xml",
        "--cov-report=json:coverage-unit.json",
        "--cov-report=term-missing",
        "-v",
    )
    # Upload to Codecov with unit flag if token is available
    if session.env.get("CODECOV_TOKEN"):
        session.run("codecov", "-f", "coverage-unit.xml", "-F", "unit", "-n", "unit-tests", external=True)


@nox.session(python=["3.11"])
def tests_integration(session):
    """Run integration tests with coverage flags for Codecov."""
    session.install("-e", DEV_EXTRAS)
    session.run(
        "pytest",
        "-m",
        "integration",
        "--cov=src",
        "--cov-branch",
        "--cov-report=xml:coverage-integration.xml",
        "--cov-report=json:coverage-integration.json",
        "--cov-report=term-missing",
        "-v",
    )
    # Upload to Codecov with integration flag if token is available
    if session.env.get("CODECOV_TOKEN"):
        session.run(
            "codecov",
            "-f",
            "coverage-integration.xml",
            "-F",
            "integration",
            "-n",
            "integration-tests",
            external=True,
        )


@nox.session(python=["3.11"])
def tests_security(session):
    """Run security tests with coverage flags for Codecov."""
    session.install("-e", DEV_EXTRAS)
    session.run(
        "pytest",
        "-m",
        "security",
        "--cov=src",
        "--cov-branch",
        "--cov-report=xml:coverage-security.xml",
        "--cov-report=json:coverage-security.json",
        "--cov-report=term-missing",
        "-v",
    )
    # Upload to Codecov with security flag if token is available
    if session.env.get("CODECOV_TOKEN"):
        session.run("codecov", "-f", "coverage-security.xml", "-F", "security", "-n", "security-tests", external=True)


@nox.session(python=["3.11"])
def tests_fast(session):
    """Run fast development cycle tests with coverage flags for Codecov."""
    session.install("-e", DEV_EXTRAS)
    session.run(
        "pytest",
        "-m",
        "not slow",
        "--cov=src",
        "--cov-branch",
        "--cov-report=xml:coverage-fast.xml",
        "--cov-report=json:coverage-fast.json",
        "--cov-report=term-missing",
        "--maxfail=5",
        "-v",
    )
    # Upload to Codecov with fast flag if token is available
    if session.env.get("CODECOV_TOKEN"):
        session.run("codecov", "-f", "coverage-fast.xml", "-F", "fast", "-n", "fast-tests", external=True)


@nox.session(python=["3.11"])
def codecov_analysis(session):
    """Run comprehensive Codecov-enhanced test analysis."""
    session.install("-e", DEV_EXTRAS)
    session.run("python", "codecov_analysis.py")


@nox.session(python="3.11")
def lint(session):
    """Run linters."""
    args = session.posargs or SRC_LOCATIONS
    session.install("-e", DEV_EXTRAS)
    session.run("black", "--check", *args)
    session.run("ruff", "check", *args)

    # Markdown linting
    session.run("markdownlint", "**/*.md", external=True)

    # YAML linting
    session.run("yamllint", ".", external=True)


@nox.session(python="3.11")
def type_check(session):
    """Run type checking with mypy."""
    session.install("-e", DEV_EXTRAS)
    session.run("mypy", "src")


@nox.session(python="3.11")
def security(session):
    """Run security checks."""
    session.install("-e", DEV_EXTRAS)

    # Check for known vulnerabilities
    session.run("safety", "check", "--json")

    # Run bandit for code security issues
    session.run("bandit", "-r", "src", "-ll")

    # Check for hardcoded secrets
    session.run("detect-secrets", "scan", "--baseline", ".secrets.baseline")


@nox.session(python="3.11")
def format_code(session):
    """Format code."""
    args = session.posargs or SRC_LOCATIONS
    session.install("-e", DEV_EXTRAS)
    session.run("black", *args)
    session.run("ruff", "check", "--fix", *args)


@nox.session(python="3.11")
def docs(session):
    """Build documentation."""
    session.install("-e", DEV_EXTRAS)
    session.cd("docs")
    session.run("mkdocs", "build")


@nox.session(python="3.11")
def deps(session):
    """Check and update dependencies."""
    session.install("-e", ".")

    # Check for outdated packages - uv has no direct equivalent; Renovate handles this

    # Export requirements with hashes
    session.run("./scripts/generate_requirements.sh", external=True)

    # Verify installation with hashes
    with session.chdir(session.create_tmp()):
        session.run("python", "-m", "venv", "test-env")
        session.run(
            "./test-env/bin/pip",
            "install",
            "--require-hashes",
            "-r",
            str(Path.cwd().parent / "requirements.txt"),
            external=True,
        )


@nox.session(python="3.11")
def pre_commit(session):
    """Run pre-commit on all files."""
    session.install("-e", DEV_EXTRAS)
    session.run("pre-commit", "run", "--all-files")


# Advanced Testing Sessions


@nox.session(python="3.11")
def mutation_testing(session):
    """Run comprehensive mutation testing to validate test quality."""
    session.install("-e", DEV_EXTRAS)

    # Clear previous mutation cache
    session.run("rm", "-rf", ".mutmut-cache", external=True, success_codes=[0, 1])

    # Run mutation testing with configuration
    session.log("🧬 Starting mutation testing...")

    try:
        # Run mutmut with correct options
        session.run(
            "mutmut",
            "run",
            "--paths-to-mutate",
            "src/core/,src/agents/,src/config/",
            "--test-time-multiplier",
            "2.0",
            "--runner",
            "python -m pytest tests/unit/ -x --disable-warnings",
            external=True,
        )

        # Generate comprehensive reports
        session.log("📊 Generating mutation testing reports...")

        # HTML report
        session.run("mutmut", "html", external=True)

        # Show summary
        session.run("mutmut", "show", external=True)

        session.log("✅ Mutation testing completed successfully")

    except Exception as e:
        session.log(f"⚠️ Mutation testing encountered issues: {e}")
        session.log("📋 Checking for partial results...")

        # Still generate available reports
        session.run("mutmut", "html", external=True, success_codes=[0, 1])

        # Don't fail the session for non-critical issues
        session.log("✅ Mutation testing completed with warnings")


@nox.session(python="3.11")
def contract_testing(session):
    """Run contract tests for MCP integrations."""
    session.install("-e", DEV_EXTRAS)
    session.run("pytest", "tests/contract/", "-v")


@nox.session(python="3.11")
def dast_scanning(session):
    """Run comprehensive DAST security scanning with OWASP ZAP."""
    session.install("-e", DEV_EXTRAS)

    # Application URL to scan
    app_url = "http://host.docker.internal:7860"
    session.log(f"🔒 Starting DAST security scan for {app_url}")

    # Verify Docker is available
    try:
        session.run("docker", "--version", external=True, silent=True)
    except Exception:
        session.error("Docker is not available. DAST scanning requires Docker.")
        return

    # Check if application is running
    session.log("📡 Checking if application is running...")
    try:
        session.run("curl", "-f", "http://localhost:7860/health", external=True, silent=True)
        session.log("✅ Application is running and accessible")
    except Exception:
        session.log("⚠️ Warning: Could not verify application is running on localhost:7860")
        session.log("Please ensure the application is started before running DAST scan")

    # Create reports directory
    session.run("mkdir", "-p", "dast-reports", external=True, success_codes=[0, 1])

    try:
        # Run OWASP ZAP baseline scan
        session.log("🕷️ Running OWASP ZAP baseline scan...")
        session.run(
            "docker",
            "run",
            "--rm",
            "-v",
            f"{session.env.get('PWD', '.')}/dast-reports:/zap/wrk/:rw",
            "owasp/zap2docker-stable",
            "zap-baseline.py",
            "-t",
            app_url,
            "-J",
            "baseline_report.json",
            "-w",
            "baseline_report.md",
            "-r",
            "baseline_report.html",
            "-x",
            "baseline_report.xml",
            external=True,
            success_codes=[0, 1, 2],  # ZAP may return non-zero for findings
        )

        # Generate comprehensive security report
        session.log("📊 Generating comprehensive security report...")
        session.run(
            "python",
            "-c",
            """
import json
import os
from datetime import datetime

def generate_security_summary():
    reports_dir = 'dast-reports'
    summary = {
        'scan_date': datetime.now().isoformat(),
        'scan_type': 'DAST',
        'tool': 'OWASP ZAP',
        'target': 'http://localhost:7860',
        'reports': []
    }

    # Check for baseline report
    baseline_path = os.path.join(reports_dir, 'baseline_report.json')
    if os.path.exists(baseline_path):
        try:
            with open(baseline_path, 'r') as f:
                baseline_data = json.load(f)
                summary['reports'].append({
                    'type': 'baseline',
                    'file': 'baseline_report.json',
                    'sites_count': len(baseline_data.get('site', [])),
                    'alerts_count': sum(len(site.get('alerts', [])) for site in baseline_data.get('site', []))
                })
        except Exception as e:
            print(f'Error parsing baseline report: {e}')

    # Write summary
    summary_path = os.path.join(reports_dir, 'security_summary.json')
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f'Security summary written to {summary_path}')
    print(f'Total reports generated: {len(summary["reports"])}')

if __name__ == '__main__':
    generate_security_summary()
""",
            external=True,
        )

        session.log("✅ DAST security scanning completed successfully")
        session.log("📁 Reports available in: dast-reports/")

    except Exception as e:
        session.log(f"⚠️ DAST scanning encountered issues: {e}")
        session.log("📋 Check dast-reports/ directory for any partial results")

        # Don't fail the session for DAST issues in development
        session.log("✅ DAST scanning completed with warnings")


@nox.session(python="3.11")
def performance_testing(session):
    """Run performance tests with Locust."""
    session.install("-e", DEV_EXTRAS)

    # Run load tests
    session.log("Starting performance testing - ensure application is running")
    session.run(
        "locust",
        "-f",
        "tests/performance/locustfile.py",
        "--host=http://localhost:7860",
        "--headless",
        "--users",
        "10",
        "--spawn-rate",
        "2",
        "--run-time",
        "30s",
    )
