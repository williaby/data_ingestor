#!/usr/bin/env python3
"""Generate ``docs/api/postman-collection.json`` from ``docs/api/openapi.json``.

Produces a Postman Collection v2.1 document with:

* ``{{baseUrl}}`` and ``{{apiKey}}`` collection variables.
* One folder per OpenAPI tag.
* A status-code assertion and a JSON-body-shape assertion per request.
* A sample request body for the ingest endpoint.

Usage::

    poetry run python scripts/generate_postman_collection.py \
        [--openapi docs/api/openapi.json] [--out docs/api/postman-collection.json]
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OPENAPI = REPO_ROOT / "docs" / "api" / "openapi.json"
DEFAULT_OUT = REPO_ROOT / "docs" / "api" / "postman-collection.json"

# Per-operation request body examples. Keyed by ``"<METHOD> <path>"``.
REQUEST_BODY_EXAMPLES: dict[str, dict[str, Any]] = {
    "POST /ingest": {
        "file_path": "/data/inbox/sample.pdf",
        "chunking_strategy": "basic",
        "metadata": {"source": "postman-newman-smoke-test"},
    },
}


def _path_to_postman_segments(path: str) -> list[str]:
    """Convert an OpenAPI path template to Postman path segments."""
    parts = [p for p in path.strip("/").split("/") if p]
    converted: list[str] = []
    for part in parts:
        if part.startswith("{") and part.endswith("}"):
            converted.append(f":{part[1:-1]}")
        else:
            converted.append(part)
    return converted


# Default values for path-variable substitution in the Postman collection. Keyed by
# the OpenAPI path-variable name; values may reference collection variables.
PATH_VARIABLE_DEFAULTS: dict[str, str] = {
    "job_id": "{{jobId}}",
}


def _path_variables(path: str) -> list[dict[str, str]]:
    """Extract Postman path variables from an OpenAPI path template."""
    variables: list[dict[str, str]] = []
    for part in path.strip("/").split("/"):
        if part.startswith("{") and part.endswith("}"):
            key = part[1:-1]
            variables.append({"key": key, "value": PATH_VARIABLE_DEFAULTS.get(key, "")})
    return variables


def _expected_status_code(operation: dict[str, Any]) -> int:
    """Return the lowest 2xx status code declared on the operation (default 200)."""
    codes = [int(c) for c in operation.get("responses", {}) if c.isdigit() and 200 <= int(c) < 300]
    return min(codes) if codes else 200


EXTRA_TEST_LINES: dict[str, list[str]] = {
    "POST /ingest": [
        "pm.test(\"Response carries a job_id and queued state\", function () {",
        "    const body = pm.response.json();",
        "    pm.expect(body).to.have.property('job_id').that.is.a('string');",
        "    pm.expect(body).to.have.property('state', 'queued');",
        "    pm.collectionVariables.set('jobId', body.job_id);",
        "});",
    ],
    "GET /ingest/{job_id}/status": [
        "pm.test(\"Response describes the same job_id\", function () {",
        "    const body = pm.response.json();",
        "    const expected = pm.collectionVariables.get('jobId');",
        "    pm.expect(body).to.have.property('job_id', expected);",
        "});",
    ],
    "GET /health": [
        "pm.test(\"status field is 'ok'\", function () {",
        "    pm.expect(pm.response.json()).to.have.property('status', 'ok');",
        "});",
    ],
}


def _build_test_script(
    operation_key: str, expected_status: int, has_json_body: bool
) -> list[str]:
    """Return the Postman test-script lines for an operation."""
    lines = [
        f"pm.test(\"Status code is {expected_status}\", function () {{",
        f"    pm.response.to.have.status({expected_status});",
        "});",
    ]
    if has_json_body and expected_status != 204:
        lines += [
            "pm.test(\"Response body is valid JSON\", function () {",
            "    pm.response.to.be.json;",
            "    const body = pm.response.json();",
            "    pm.expect(body).to.be.an('object');",
            "});",
        ]
    lines += EXTRA_TEST_LINES.get(operation_key, [])
    return lines


def _build_request_body(
    operation_key: str, operation: dict[str, Any]
) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    """Return the (body, headers) pair for a Postman request item."""
    request_body = operation.get("requestBody")
    if not request_body:
        return None, []

    content = request_body.get("content", {})
    if "application/json" not in content:
        return None, []

    example = REQUEST_BODY_EXAMPLES.get(operation_key, {})
    return (
        {
            "mode": "raw",
            "raw": json.dumps(example, indent=2),
            "options": {"raw": {"language": "json"}},
        },
        [{"key": "Content-Type", "value": "application/json"}],
    )


def _build_item(method: str, path: str, operation: dict[str, Any]) -> dict[str, Any]:
    """Build one Postman request item from an OpenAPI operation."""
    operation_key = f"{method.upper()} {path}"
    segments = _path_to_postman_segments(path)
    body, body_headers = _build_request_body(operation_key, operation)

    headers = [{"key": "X-API-Key", "value": "{{apiKey}}"}, *body_headers]

    expected_status = _expected_status_code(operation)
    test_lines = _build_test_script(operation_key, expected_status, has_json_body=True)

    request: dict[str, Any] = {
        "method": method.upper(),
        "header": headers,
        "url": {
            "raw": "{{baseUrl}}/" + "/".join(segments),
            "host": ["{{baseUrl}}"],
            "path": segments,
            "variable": _path_variables(path),
        },
        "description": operation.get("description") or operation.get("summary", ""),
    }
    if body is not None:
        request["body"] = body

    item: dict[str, Any] = {
        "name": operation.get("summary") or operation_key,
        "request": request,
        "response": [],
        "event": [
            {
                "listen": "test",
                "script": {"type": "text/javascript", "exec": test_lines},
            }
        ],
    }
    return item


def build_collection(openapi: dict[str, Any]) -> dict[str, Any]:
    """Build a Postman Collection v2.1 dictionary from an OpenAPI schema."""
    info = openapi.get("info", {})

    items_by_tag: dict[str, list[dict[str, Any]]] = defaultdict(list)
    untagged: list[dict[str, Any]] = []

    for path, methods in openapi.get("paths", {}).items():
        for method, operation in methods.items():
            if method.lower() not in {"get", "post", "put", "delete", "patch"}:
                continue
            item = _build_item(method, path, operation)
            tags = operation.get("tags") or []
            if tags:
                items_by_tag[tags[0]].append(item)
            else:
                untagged.append(item)

    # Order folders so Newman exercises health → ingest (which captures jobId) → status.
    folder_order = ["health", "ingest", "status"]

    def _folder_sort_key(name: str) -> tuple[int, str]:
        return (folder_order.index(name), name) if name in folder_order else (len(folder_order), name)

    folders: list[dict[str, Any]] = []
    for tag_name in sorted(items_by_tag, key=_folder_sort_key):
        # Within the ingest folder, the POST must run before the GET-by-id.
        items = items_by_tag[tag_name]
        if tag_name == "ingest":
            items = sorted(items, key=lambda it: 0 if it["request"]["method"] == "POST" else 1)
        folders.append(
            {
                "name": tag_name,
                "description": f"Endpoints tagged '{tag_name}'.",
                "item": items,
            }
        )
    if untagged:
        folders.append({"name": "untagged", "item": untagged})

    return {
        "info": {
            "name": info.get("title", "Data Ingestor API"),
            "description": info.get("description", ""),
            "version": info.get("version", "0.0.0"),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            "_postman_id": "data-ingestor-api",
        },
        "item": folders,
        "variable": [
            {"key": "baseUrl", "value": "http://localhost:8000", "type": "string"},
            {"key": "apiKey", "value": "", "type": "string"},
            {"key": "jobId", "value": "", "type": "string"},
        ],
        "event": [
            {
                "listen": "prerequest",
                "script": {
                    "type": "text/javascript",
                    "exec": [
                        "// Ensure baseUrl has no trailing slash",
                        "const base = pm.variables.get('baseUrl') || '';",
                        "if (base.endsWith('/')) {",
                        "    pm.variables.set('baseUrl', base.replace(/\\/+$/, ''));",
                        "}",
                    ],
                },
            }
        ],
    }


def main() -> int:
    """CLI entry point; returns a process exit code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openapi", type=Path, default=DEFAULT_OPENAPI)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    openapi = json.loads(args.openapi.read_text(encoding="utf-8"))
    collection = build_collection(openapi)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(collection, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote Postman collection to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
