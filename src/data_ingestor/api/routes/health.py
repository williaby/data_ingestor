"""Health-stage routes: liveness probe and parser availability report."""

from __future__ import annotations

from fastapi import APIRouter, status

from data_ingestor.api import state
from data_ingestor.api.models import (
    ErrorResponse,
    HealthStatus,
    ParserHealth,
    ParserHealthReport,
)
from data_ingestor.core.config import Settings
from data_ingestor.core.models import DocumentFormat
from data_ingestor.pipeline.router import ParserRegistry

router = APIRouter(tags=["health"])

_SETTINGS = Settings()


@router.get(
    "/health",
    summary="Liveness probe",
    response_model=HealthStatus,
    status_code=status.HTTP_200_OK,
    responses={503: {"model": ErrorResponse, "description": "Service unavailable"}},
)
async def health() -> HealthStatus:
    """Report API process liveness.

    Pipeline stage: ``health`` — this endpoint does not invoke any parser or storage code;
    it only confirms that the API process is accepting requests.

    Async response structure: a :class:`HealthStatus` payload with three fields —
    ``status`` (literal ``"ok"`` while serving), ``version`` (application version), and
    ``uptime_seconds`` (float since process start).
    """
    return HealthStatus(
        status="ok",
        version=_SETTINGS.version,
        uptime_seconds=state.uptime_seconds(),
    )


@router.get(
    "/health/parsers",
    summary="Parser availability report",
    response_model=ParserHealthReport,
    status_code=status.HTTP_200_OK,
)
async def parser_health() -> ParserHealthReport:
    """Report which parsers are registered for each supported document format.

    Pipeline stage: ``health`` — surfaces the ``ParserRegistry`` view of the routing layer
    without invoking any parser. Used by readiness gates and by the Newman CI workflow
    to confirm the service is wired up correctly before exercising ingest.

    Async response structure: a :class:`ParserHealthReport` payload with a top-level
    ``healthy`` boolean (true when every format has at least one parser registered) and
    a ``formats`` list of :class:`ParserHealth` entries, each carrying the format
    identifier, an ``available`` flag, and the registered parser names ordered by
    priority.
    """
    registry = ParserRegistry()
    entries: list[ParserHealth] = []
    for fmt in DocumentFormat:
        if fmt is DocumentFormat.UNKNOWN:
            continue
        parsers = registry.get_parsers(fmt)
        entries.append(
            ParserHealth(
                format=fmt.value,
                available=bool(parsers),
                parsers=[p.name for p in parsers],
            )
        )
    return ParserHealthReport(
        healthy=all(e.available for e in entries) if entries else False,
        formats=entries,
    )
