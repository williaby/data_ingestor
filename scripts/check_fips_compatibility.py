#!/usr/bin/env python3
"""FIPS 140-2/140-3 compatibility checker.

Statically scans Python sources for cryptographic usage that is not permitted
when the host runs in FIPS mode (e.g. Ubuntu with the fips-updates packages).

Findings are graded:

* ``error``   - non-approved primitive used for security (fails the check)
* ``warning`` - usage that needs human verification (fails only in --strict)
* ``info``    - benign usage worth noting (never fails)

The script intentionally depends only on the standard library so it can run in
any minimal CI image.

Usage::

    python scripts/check_fips_compatibility.py [--include-tests] [--strict]
                                               [--fix-hints] [--json]

Exit code is non-zero when errors are present (or warnings in --strict mode).
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Hash algorithms not approved under FIPS when used for security purposes.
NON_APPROVED_HASHES = {"md5", "md4", "sha1", "ripemd160", "md5sha1"}

# Symmetric ciphers / primitives that FIPS does not approve.
NON_APPROVED_CIPHERS = {"des", "des3", "3des", "arc2", "arc4", "rc2", "rc4", "blowfish", "cast", "idea"}

# Modules that historically bundle non-approved crypto implementations.
SUSPECT_CRYPTO_MODULES = {"Crypto", "Cryptodome", "pycrypto"}

# TLS/SSL protocol constants that are not FIPS-approved.
WEAK_TLS_CONSTANTS = {"PROTOCOL_SSLv2", "PROTOCOL_SSLv3", "PROTOCOL_TLSv1", "PROTOCOL_TLSv1_1", "SSLv23"}

FIX_HINTS = {
    "hash": "Use hashlib.sha256/sha384/sha512, or pass usedforsecurity=False for non-security digests.",
    "cipher": "Use AES (via the 'cryptography' package's Cipher with an approved mode) instead.",
    "module": "Prefer the 'cryptography' package, which can use the system OpenSSL FIPS provider.",
    "tls": "Use ssl.PROTOCOL_TLS_CLIENT/SERVER and require TLS 1.2+.",
    "random": "If this value is security-sensitive, use the 'secrets' module instead of 'random'.",
}

SEVERITY_ORDER = ("error", "warning", "info")


@dataclass
class Finding:
    """A single FIPS-relevant observation."""

    severity: str
    category: str
    path: str
    line: int
    message: str

    def hint(self) -> str:
        """Return a remediation hint for this finding's category."""
        return FIX_HINTS.get(self.category, "")


@dataclass
class Report:
    """Aggregated scan results."""

    findings: list[Finding] = field(default_factory=list)

    def add(self, finding: Finding) -> None:
        """Record a finding."""
        self.findings.append(finding)

    def count(self, severity: str) -> int:
        """Return the number of findings of the given severity."""
        return sum(1 for f in self.findings if f.severity == severity)

    @property
    def summary(self) -> dict[str, int]:
        """Return error/warning/info counts."""
        return {
            "errors": self.count("error"),
            "warnings": self.count("warning"),
            "info": self.count("info"),
        }


class _CryptoVisitor(ast.NodeVisitor):
    """AST visitor that flags non-FIPS cryptographic usage in one module."""

    def __init__(self, report: Report, rel_path: str) -> None:
        self._report = report
        self._path = rel_path

    def _emit(self, severity: str, category: str, line: int, message: str) -> None:
        self._report.add(Finding(severity, category, self._path, line, message))

    @staticmethod
    def _attr_chain(node: ast.AST) -> str:
        """Return a dotted name for an attribute/name expression, else ''."""
        parts: list[str] = []
        current: ast.AST | None = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802 (ast API)
        for alias in node.names:
            top = alias.name.split(".")[0]
            if top in SUSPECT_CRYPTO_MODULES:
                self._emit("warning", "module", node.lineno, f"imports non-FIPS crypto module '{alias.name}'")
            elif top == "random":
                self._emit("info", "random", node.lineno, "imports 'random' (ensure not used for security)")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802 (ast API)
        top = (node.module or "").split(".")[0]
        if top in SUSPECT_CRYPTO_MODULES:
            self._emit("warning", "module", node.lineno, f"imports from non-FIPS crypto module '{node.module}'")
        elif top == "random":
            self._emit("info", "random", node.lineno, "imports from 'random' (ensure not used for security)")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802 (ast API)
        dotted = self._attr_chain(node.func)
        name = dotted.split(".")[-1].lower()
        used_for_security = self._used_for_security(node)

        # hashlib.md5(...) / hashlib.sha1(...) and friends
        if "hashlib" in dotted and name in NON_APPROVED_HASHES:
            if used_for_security:
                self._emit("error", "hash", node.lineno, f"non-approved hash '{name}' used for security")
            else:
                self._emit("info", "hash", node.lineno, f"non-approved hash '{name}' with usedforsecurity=False")

        # hashlib.new("md5", ...)
        if dotted.endswith("hashlib.new") and node.args and isinstance(node.args[0], ast.Constant):
            algo = str(node.args[0].value).lower()
            if algo in NON_APPROVED_HASHES:
                severity = "info" if not used_for_security else "error"
                self._emit(severity, "hash", node.lineno, f"hashlib.new('{algo}')")

        # Non-approved symmetric ciphers referenced by name
        if name in NON_APPROVED_CIPHERS and "." in dotted:
            self._emit("error", "cipher", node.lineno, f"non-approved cipher '{name}' referenced")

        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:  # noqa: N802 (ast API)
        if node.attr in WEAK_TLS_CONSTANTS:
            self._emit("warning", "tls", node.lineno, f"weak TLS constant '{node.attr}'")
        self.generic_visit(node)

    @staticmethod
    def _used_for_security(node: ast.Call) -> bool:
        """Return False only when an explicit usedforsecurity=False is passed."""
        for kw in node.keywords:
            if kw.arg == "usedforsecurity" and isinstance(kw.value, ast.Constant):
                return bool(kw.value.value)
        return True


def _iter_python_files(include_tests: bool) -> list[Path]:
    root = Path(__file__).resolve().parent.parent
    files: list[Path] = sorted((root / "src").rglob("*.py"))
    if include_tests:
        tests_dir = root / "tests"
        if tests_dir.is_dir():
            files += sorted(tests_dir.rglob("*.py"))
    return files


def scan(include_tests: bool) -> Report:
    """Scan the project's Python sources and return a report."""
    report = Report()
    root = Path(__file__).resolve().parent.parent
    for path in _iter_python_files(include_tests):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError) as exc:
            report.add(Finding("warning", "module", str(path), 0, f"could not parse: {exc}"))
            continue
        try:
            rel = str(path.relative_to(root))
        except ValueError:
            rel = str(path)
        _CryptoVisitor(report, rel).visit(tree)
    return report


def _print_text(report: Report, show_hints: bool) -> None:
    print("FIPS 140-2/140-3 Compatibility Report")
    print("=" * 38)
    if not report.findings:
        print("No cryptographic concerns detected.")
    for severity in SEVERITY_ORDER:
        items = [f for f in report.findings if f.severity == severity]
        if not items:
            continue
        print(f"\n{severity.upper()} ({len(items)}):")
        for f in items:
            print(f"  {f.path}:{f.line}: {f.message}")
            if show_hints and f.hint():
                print(f"      hint: {f.hint()}")
    s = report.summary
    print(f"\nSummary: {s['errors']} error(s), {s['warnings']} warning(s), {s['info']} info")


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns the process exit code."""
    parser = argparse.ArgumentParser(description="Check Python sources for FIPS compatibility.")
    parser.add_argument("--include-tests", action="store_true", help="also scan the tests/ directory")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    parser.add_argument("--fix-hints", action="store_true", help="print remediation hints")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = parser.parse_args(argv)

    report = scan(include_tests=args.include_tests)

    if args.json:
        payload = {
            "summary": report.summary,
            "findings": [
                {
                    "severity": f.severity,
                    "category": f.category,
                    "path": f.path,
                    "line": f.line,
                    "message": f.message,
                }
                for f in report.findings
            ],
        }
        print(json.dumps(payload, indent=2))
    else:
        _print_text(report, show_hints=args.fix_hints)

    summary = report.summary
    if summary["errors"] > 0:
        return 1
    if args.strict and summary["warnings"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
