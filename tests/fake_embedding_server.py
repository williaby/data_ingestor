"""A fake OpenAI-compatible embeddings server for tests.

Runs a real HTTP server on an ephemeral local port. Vectors are deterministic
bag-of-words hashes, so texts that share words get similar vectors and search
tests can assert on ranking without any model.
"""

import hashlib
import json
import math
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

DIMENSIONS = 1024
TEST_KEY = "test-embed-key"


def fake_vector(text: str) -> list[float]:
    vector = [0.0] * DIMENSIONS
    for word in text.lower().split():
        bucket = int(hashlib.sha256(word.encode()).hexdigest(), 16) % DIMENSIONS
        vector[bucket] += 1.0
    norm = math.sqrt(sum(x * x for x in vector)) or 1.0
    return [x / norm for x in vector]


class FakeEmbeddingServer:
    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        self.dimensions = DIMENSIONS
        self.fail_with: int | None = None
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                outer.requests.append(
                    {"path": self.path, "auth": self.headers.get("Authorization"), "body": body},
                )
                if self.headers.get("Authorization") != f"Bearer {TEST_KEY}":
                    self._send(401, {"error": "unauthorized"})
                    return
                if outer.fail_with:
                    self._send(outer.fail_with, {"error": "forced"})
                    return
                inputs = body["input"] if isinstance(body["input"], list) else [body["input"]]
                data = [
                    {"object": "embedding", "index": i, "embedding": fake_vector(text)[: outer.dimensions]}
                    for i, text in enumerate(inputs)
                ]
                self._send(200, {"object": "list", "model": body.get("model"), "data": data})

            def _send(self, status: int, payload: dict[str, Any]) -> None:
                raw = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def log_message(self, *_args: object) -> None:  # keep test output quiet
                return

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self._server.server_address[1]}"
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()


@contextmanager
def running_fake_embedding_server() -> Iterator[FakeEmbeddingServer]:
    server = FakeEmbeddingServer()
    server.start()
    try:
        yield server
    finally:
        server.stop()
