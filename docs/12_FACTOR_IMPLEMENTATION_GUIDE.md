# 12 Factor App Implementation Guide

**Project**: data_ingestor
**Priority**: Critical Fixes → High Priority → Medium Priority
**Estimated Total Effort**: 3-4 weeks

This guide provides step-by-step implementation instructions for achieving 12 Factor App compliance.

---

## Quick Start: Critical Fixes (Week 1)

### 🔴 Factor 9: Implement Graceful Shutdown

**Priority**: CRITICAL
**Effort**: 2-3 days
**Impact**: Production reliability, data integrity

#### Problem
The application does not handle SIGTERM signals, causing:
- Interrupted HTTP requests during deployment
- Lost Celery tasks during shutdown
- Unclosed database connections
- Data corruption risk

#### Solution: Add Lifecycle Management

**Step 1: Create shutdown handler module**

```python
# src/data_ingestor/core/lifecycle.py
"""Application lifecycle management for graceful startup/shutdown."""

import asyncio
import logging
import signal
from typing import Any, Callable

logger = logging.getLogger(__name__)


class LifecycleManager:
    """Manages application startup and shutdown lifecycle."""

    def __init__(self) -> None:
        """Initialize lifecycle manager."""
        self.shutdown_handlers: list[Callable[[], Any]] = []
        self.startup_handlers: list[Callable[[], Any]] = []
        self._shutdown_event = asyncio.Event()

    def on_startup(self, handler: Callable[[], Any]) -> None:
        """Register startup handler.

        Args:
            handler: Async or sync function to call on startup
        """
        self.startup_handlers.append(handler)

    def on_shutdown(self, handler: Callable[[], Any]) -> None:
        """Register shutdown handler.

        Args:
            handler: Async or sync function to call on shutdown
        """
        self.shutdown_handlers.append(handler)

    async def startup(self) -> None:
        """Run all startup handlers."""
        logger.info("application_startup_begin", handler_count=len(self.startup_handlers))

        for handler in self.startup_handlers:
            handler_name = handler.__name__
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler()
                else:
                    handler()
                logger.info("startup_handler_success", handler=handler_name)
            except Exception as e:
                logger.error("startup_handler_failed", handler=handler_name, error=str(e))
                raise

        logger.info("application_startup_complete")

    async def shutdown(self, timeout: float = 30.0) -> None:
        """Run all shutdown handlers with timeout.

        Args:
            timeout: Maximum time to wait for graceful shutdown (seconds)
        """
        logger.info("application_shutdown_begin", timeout=timeout, handler_count=len(self.shutdown_handlers))
        self._shutdown_event.set()

        # Run shutdown handlers with timeout
        try:
            async with asyncio.timeout(timeout):
                for handler in reversed(self.shutdown_handlers):  # LIFO order
                    handler_name = handler.__name__
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler()
                        else:
                            handler()
                        logger.info("shutdown_handler_success", handler=handler_name)
                    except Exception as e:
                        logger.error("shutdown_handler_failed", handler=handler_name, error=str(e))
                        # Continue with other handlers even if one fails

            logger.info("application_shutdown_complete", duration_ms=0)

        except TimeoutError:
            logger.error("shutdown_timeout_exceeded", timeout=timeout)
            # Force exit after timeout
            raise

    def setup_signal_handlers(self, loop: asyncio.AbstractEventLoop) -> None:
        """Setup SIGTERM and SIGINT handlers.

        Args:
            loop: Event loop to register signal handlers with
        """
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda s=sig: asyncio.create_task(self._handle_signal(s))
            )
        logger.info("signal_handlers_registered", signals=["SIGTERM", "SIGINT"])

    async def _handle_signal(self, sig: signal.Signals) -> None:
        """Handle shutdown signals.

        Args:
            sig: Signal received
        """
        logger.warning("shutdown_signal_received", signal=sig.name)
        await self.shutdown()


# Global instance
lifecycle = LifecycleManager()
```

**Step 2: Integrate with FastAPI**

```python
# src/data_ingestor/api/app.py (or src/main.py)
"""FastAPI application with graceful shutdown."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from data_ingestor.core.config import Settings
from data_ingestor.core.lifecycle import lifecycle

settings = Settings()

# Database engine
engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Redis client
redis_client = Redis.from_url(
    settings.redis_url,
    decode_responses=True,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    await lifecycle.startup()

    # Register shutdown handlers
    lifecycle.on_shutdown(close_database)
    lifecycle.on_shutdown(close_redis)
    lifecycle.on_shutdown(drain_connections)

    yield

    # Shutdown
    await lifecycle.shutdown(timeout=30.0)


async def close_database() -> None:
    """Close database connections."""
    logger.info("closing_database_connections")
    await engine.dispose()


async def close_redis() -> None:
    """Close Redis connections."""
    logger.info("closing_redis_connections")
    await redis_client.aclose()


async def drain_connections(timeout: float = 30.0) -> None:
    """Drain active HTTP connections.

    Args:
        timeout: Maximum time to wait for connections to drain
    """
    logger.info("draining_connections", timeout=timeout)

    # Wait for active requests to complete
    # FastAPI/Uvicorn handles this automatically, but we log it
    await asyncio.sleep(0.1)  # Brief pause for logging

    logger.info("connections_drained")


# Create FastAPI app with lifespan
app = FastAPI(
    title="Data Ingestor",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/readiness")
async def readiness_check() -> dict[str, str]:
    """Readiness check endpoint (K8s)."""
    # Check database connection
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
    except Exception:
        return {"status": "not_ready", "reason": "database_unavailable"}

    # Check Redis connection
    try:
        await redis_client.ping()
    except Exception:
        return {"status": "not_ready", "reason": "redis_unavailable"}

    return {"status": "ready"}
```

**Step 3: Configure Uvicorn for graceful shutdown**

```python
# src/data_ingestor/server.py
"""Production server with graceful shutdown."""

import asyncio
import logging
import signal

import uvicorn

from data_ingestor.core.config import Settings
from data_ingestor.core.lifecycle import lifecycle

logger = logging.getLogger(__name__)
settings = Settings()


class Server:
    """Uvicorn server with graceful shutdown."""

    def __init__(self) -> None:
        """Initialize server."""
        self.server: uvicorn.Server | None = None
        self.should_exit = False

    async def start(self) -> None:
        """Start server with graceful shutdown handlers."""
        config = uvicorn.Config(
            "data_ingestor.api.app:app",
            host=settings.api_host,
            port=settings.api_port,
            workers=settings.api_workers,
            loop="asyncio",
            log_level=settings.log_level.lower(),
        )

        self.server = uvicorn.Server(config)

        # Setup signal handlers
        loop = asyncio.get_event_loop()
        lifecycle.setup_signal_handlers(loop)

        # Override Uvicorn's signal handlers
        self.server.install_signal_handlers = lambda: None

        # Run server
        logger.info("server_starting", host=settings.api_host, port=settings.api_port)
        await self.server.serve()

    async def shutdown(self) -> None:
        """Shutdown server gracefully."""
        if self.server:
            logger.info("server_shutdown_initiated")
            self.server.should_exit = True
            await asyncio.sleep(0.1)  # Allow time for shutdown signal


def run() -> None:
    """Run production server."""
    server = Server()

    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("server_interrupted")
    finally:
        logger.info("server_stopped")


if __name__ == "__main__":
    run()
```

**Step 4: Update Dockerfile CMD**

```dockerfile
# Dockerfile (update line 62)
CMD ["python", "-m", "data_ingestor.server"]
```

**Step 5: Test graceful shutdown**

```bash
# Terminal 1: Start server
uv run python -m data_ingestor.server

# Terminal 2: Send requests
while true; do curl http://localhost:8000/health; sleep 0.1; done

# Terminal 3: Trigger shutdown
kill -SIGTERM $(pgrep -f "data_ingestor.server")

# Expected output:
# - No interrupted requests
# - Clean shutdown logs
# - All connections closed
# - Exit code 0
```

**Success Criteria**:
- ✅ Server responds to SIGTERM within 1 second
- ✅ Active requests complete (up to 30s timeout)
- ✅ Database connections closed cleanly
- ✅ Redis connections closed cleanly
- ✅ No error logs during shutdown
- ✅ Exit code 0 after shutdown

---

### 🔴 Factor 11: Fix Logging

**Priority**: HIGH
**Effort**: 1-2 days
**Impact**: Observability, debugging

#### Problem
- Logs written to files (`/app/logs`)
- Not all logs go to stdout
- Unstructured text logs (hard to parse)
- No request tracing

#### Solution: Structured Logging to Stdout

**Step 1: Configure structlog**

```python
# src/data_ingestor/core/logging_config.py
"""Structured logging configuration."""

import logging
import sys

import structlog


def configure_logging(log_level: str = "INFO", json_logs: bool = True) -> None:
    """Configure structured logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        json_logs: Use JSON output (True for production, False for dev)
    """
    # Convert to uppercase
    log_level = log_level.upper()

    # Configure structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_logger_name,
        structlog.processors.CallsiteParameterAdder(
            [
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.LINENO,
            ]
        ),
    ]

    if json_logs:
        # Production: JSON logs
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Development: Pretty console logs
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging to stdout
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level),
    )

    # Silence noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


# Helper to get logger
def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get structured logger.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)
```

**Step 2: Update existing logging**

```python
# Before (old style):
import logging
logger = logging.getLogger(__name__)
logger.info(f"Processing document {doc_id} with {page_count} pages")

# After (structured):
from data_ingestor.core.logging_config import get_logger
logger = get_logger(__name__)
logger.info(
    "document_processing_started",
    document_id=doc_id,
    page_count=page_count,
    parser="pymupdf",
)

# JSON output:
# {
#   "event": "document_processing_started",
#   "document_id": "abc123",
#   "page_count": 10,
#   "parser": "pymupdf",
#   "timestamp": "2025-11-18T12:34:56.789Z",
#   "level": "info",
#   "logger": "data_ingestor.parsers.pdf_parser",
#   "filename": "pdf_parser.py",
#   "lineno": 123
# }
```

**Step 3: Add request ID middleware**

```python
# src/data_ingestor/api/middleware.py
"""Request tracing middleware."""

import uuid

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Add request ID to all logs."""

    async def dispatch(self, request: Request, call_next):
        """Process request with tracing.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler
        """
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Bind request ID to context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        # Process request
        response = await call_next(request)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response


# In app.py:
from data_ingestor.api.middleware import RequestTracingMiddleware
app.add_middleware(RequestTracingMiddleware)
```

**Step 4: Remove file logging**

```dockerfile
# Dockerfile (REMOVE line 35)
# RUN mkdir -p /app/logs /app/data  # DELETE THIS LINE
```

```python
# Remove all FileHandler usage:
git grep -r "FileHandler" src/
git grep -r "filename=" src/ | grep logging

# Replace with stdout logging
```

**Step 5: Configure Sentry (optional)**

```python
# src/data_ingestor/core/logging_config.py (add to configure_logging)
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

def configure_logging(log_level: str = "INFO", json_logs: bool = True, sentry_dsn: str | None = None) -> None:
    """Configure structured logging with optional Sentry."""
    # ... existing code ...

    # Optional: Sentry integration
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=os.getenv("ENVIRONMENT", "production"),
            traces_sample_rate=0.1,  # 10% of transactions
            profiles_sample_rate=0.1,  # 10% of transactions
            integrations=[
                LoggingIntegration(
                    level=logging.INFO,  # Capture info and above
                    event_level=logging.ERROR,  # Create events for errors
                ),
            ],
        )
```

**Step 6: Update config**

```python
# src/data_ingestor/core/config.py (add)
class Settings(BaseSettings):
    # ... existing fields ...

    # Logging
    log_format: str = "json"  # json or console
    sentry_dsn: str | None = None
```

**Step 7: Test logging**

```bash
# Start server with JSON logging
DATA_INGESTOR_LOG_FORMAT=json uv run python -m data_ingestor.server

# Make request
curl http://localhost:8000/health

# Check logs are JSON to stdout:
# {"event": "http_request", "request_id": "abc-123", "method": "GET", "path": "/health", ...}

# Start server with console logging (dev)
DATA_INGESTOR_LOG_FORMAT=console uv run python -m data_ingestor.server

# Check logs are pretty-printed:
# 2025-11-18 12:34:56 [info     ] http_request  method=GET path=/health request_id=abc-123
```

**Success Criteria**:
- ✅ All logs go to stdout
- ✅ JSON format in production
- ✅ Pretty format in development
- ✅ Request ID in all log entries
- ✅ No `/app/logs` directory
- ✅ Sentry captures errors (optional)

---

## High Priority Fixes (Week 2)

### 🟡 Factor 3: Fix Configuration

**Priority**: HIGH
**Effort**: 1 day
**Impact**: Security, deployment

#### Solution: Required Environment Variables

```python
# src/data_ingestor/core/config.py (update)
from pydantic import Field

class Settings(BaseSettings):
    # ... existing model_config ...

    # REMOVE defaults for production services:
    database_url: str = Field(
        ...,  # Required, no default
        description="PostgreSQL connection URL (e.g., postgresql://user:pass@host:5432/db)",
    )

    redis_url: str = Field(
        ...,  # Required, no default
        description="Redis connection URL (e.g., redis://host:6379/0)",
    )

    # Add validation
    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format."""
        if not v.startswith(("postgresql://", "postgresql+asyncpg://")):
            raise ValueError("database_url must be a PostgreSQL connection string")
        if "localhost" in v and os.getenv("ENVIRONMENT") == "production":
            raise ValueError("database_url cannot use localhost in production")
        return v

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """Validate Redis URL format."""
        if not v.startswith("redis://"):
            raise ValueError("redis_url must be a Redis connection string")
        if "localhost" in v and os.getenv("ENVIRONMENT") == "production":
            raise ValueError("redis_url cannot use localhost in production")
        return v
```

**Update .env.example**:

```bash
# .env.example (add required vars)

# REQUIRED: Database connection
DATA_INGESTOR_DATABASE_URL=postgresql://user:password@localhost:5432/data_ingestor

# REQUIRED: Redis connection
DATA_INGESTOR_REDIS_URL=redis://localhost:6379/0

# REQUIRED: Environment
ENVIRONMENT=development  # development, staging, production
```

---

### 🟡 Factor 6: Remove Process-Local State

**Priority**: HIGH
**Effort**: 1-2 days
**Impact**: Horizontal scaling

#### Solution: Redis-Backed Caching

```python
# src/data_ingestor/core/cache.py
"""Redis-backed caching (12-factor compliant)."""

import json
from typing import Any

from redis import Redis

from data_ingestor.core.config import Settings


class RedisCache:
    """Redis-backed cache for 12-factor compliance."""

    def __init__(self, redis_url: str, prefix: str = "cache:") -> None:
        """Initialize Redis cache.

        Args:
            redis_url: Redis connection URL
            prefix: Key prefix for namespacing
        """
        self.client = Redis.from_url(redis_url, decode_responses=True)
        self.prefix = prefix

    def get(self, key: str) -> Any | None:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        value = self.client.get(f"{self.prefix}{key}")
        if value:
            return json.loads(value)
        return None

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl: Time-to-live in seconds (default: 5 minutes)
        """
        self.client.setex(
            f"{self.prefix}{key}",
            ttl,
            json.dumps(value),
        )

    def delete(self, key: str) -> None:
        """Delete value from cache.

        Args:
            key: Cache key
        """
        self.client.delete(f"{self.prefix}{key}")


# Before (process-local):
from cachetools import TTLCache
cache = TTLCache(maxsize=100, ttl=300)  # ❌ Process-local

# After (Redis-backed):
from data_ingestor.core.cache import RedisCache
cache = RedisCache(settings.redis_url)  # ✅ Shared across processes
```

---

## Medium Priority (Weeks 3-4)

### 🟢 Factor 8: Horizontal Scaling

**Create Kubernetes manifests**:

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: data-ingestor-web
spec:
  replicas: 3  # Horizontal scaling
  selector:
    matchLabels:
      app: data-ingestor
      tier: web
  template:
    metadata:
      labels:
        app: data-ingestor
        tier: web
    spec:
      containers:
      - name: web
        image: data-ingestor:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATA_INGESTOR_DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: data-ingestor-secrets
              key: database-url
        - name: DATA_INGESTOR_REDIS_URL
          valueFrom:
            secretKeyRef:
              name: data-ingestor-secrets
              key: redis-url
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /readiness
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
```

---

### 🟢 Factor 12: Admin Processes

**Add CLI commands**:

```python
# src/data_ingestor/cli/main.py (add commands)

@cli.command()
def shell() -> None:
    """Open interactive Python shell."""
    import IPython
    from data_ingestor.core.config import Settings

    settings = Settings()
    IPython.embed(banner1="Data Ingestor Shell", user_ns={"settings": settings})


@cli.group()
def db() -> None:
    """Database management."""
    pass


@db.command()
@click.option("--message", "-m", required=True)
def migrate(message: str) -> None:
    """Create migration."""
    import subprocess
    subprocess.run(["alembic", "revision", "--autogenerate", "-m", message])


@db.command()
def upgrade() -> None:
    """Run migrations."""
    import subprocess
    subprocess.run(["alembic", "upgrade", "head"])
```

---

## Validation Checklist

### Critical (Must Have)
- [ ] SIGTERM signal handling implemented
- [ ] Graceful shutdown with 30s timeout
- [ ] All logs to stdout (no /app/logs)
- [ ] Structured JSON logging
- [ ] Request ID tracing

### High Priority (Should Have)
- [ ] No hardcoded service URLs
- [ ] Required env vars validated at startup
- [ ] Redis-backed caching (no process-local)
- [ ] Sentry error tracking configured

### Medium Priority (Nice to Have)
- [ ] Kubernetes manifests
- [ ] Load balancer configuration
- [ ] Admin CLI commands (shell, db migrate)
- [ ] Alembic configured

---

## Testing Guide

### Test Graceful Shutdown

```bash
# 1. Start server
uv run python -m data_ingestor.server &
PID=$!

# 2. Send continuous requests
while true; do curl -s http://localhost:8000/health > /dev/null; done &
CURL_PID=$!

# 3. Trigger shutdown
kill -SIGTERM $PID

# 4. Wait for shutdown
wait $PID

# 5. Check exit code
echo $?  # Should be 0

# 6. Stop curl
kill $CURL_PID
```

### Test Structured Logging

```bash
# Start with JSON logging
DATA_INGESTOR_LOG_FORMAT=json uv run python -m data_ingestor.server > logs.json

# Make requests
curl http://localhost:8000/health

# Validate JSON
jq . logs.json  # Should parse successfully

# Check for request IDs
jq '.request_id' logs.json  # Should have UUIDs
```

---

## Rollout Strategy

### Phase 1: Critical Fixes (Week 1)
1. Day 1-2: Implement graceful shutdown
2. Day 3: Test in staging environment
3. Day 4: Deploy to production with monitoring
4. Day 5: Fix structured logging

### Phase 2: High Priority (Week 2)
1. Day 1: Fix configuration validation
2. Day 2: Replace process-local caching
3. Day 3-4: Test and deploy
4. Day 5: Documentation

### Phase 3: Medium Priority (Weeks 3-4)
1. Week 3: Kubernetes manifests, load balancer
2. Week 4: Admin processes, final testing

---

## Success Metrics

### Before
- Compliance: 78%
- Graceful shutdown: ❌
- Logs to stdout: ⚠️ Partial
- Horizontal scaling: ⚠️ Limited

### After Phase 1
- Compliance: 85%
- Graceful shutdown: ✅
- Logs to stdout: ✅
- Request tracing: ✅

### After Phase 2
- Compliance: 90%
- Config validation: ✅
- Stateless processes: ✅

### After Phase 3
- Compliance: 95%
- Kubernetes ready: ✅
- Admin processes: ✅

---

**Next Steps**: Start with Factor 9 (graceful shutdown) as it has the highest impact on production reliability.
