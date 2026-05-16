#!/usr/bin/env python3
"""Export the FastAPI OpenAPI schema to ``docs/api/openapi.json``.

Usage:
    poetry run python scripts/export_openapi.py [output_path]

The output path defaults to ``docs/api/openapi.json`` relative to the repo root.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data_ingestor.api.app import app  # noqa: E402


def main(argv: list[str]) -> int:
    """Write the OpenAPI schema to disk; return a process exit code."""
    if len(argv) > 1:
        output_path = Path(argv[1]).resolve()
    else:
        output_path = REPO_ROOT / "docs" / "api" / "openapi.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    schema = app.openapi()
    output_path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote OpenAPI schema to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
