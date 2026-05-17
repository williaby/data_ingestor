"""Health-stage routes: liveness probe and supported-format report."""

from __future__ import annotations

from fastapi import APIRouter, status

from data_ingestor.api import state
from data_ingestor.api.models import HealthStatus, ParserHealth, ParserHealthReport
from data_ingestor.core.config import Settings
from data_ingestor.core.models import DocumentFormat

router = APIRouter(tags=["health"])

_SETTINGS = Settings()


@router.get(
    "/health",
    summary="Liveness probe",
    response_model=HealthStatus,
    status_code=status.HTTP_200_OK,
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
    summary="Supported document formats",
    response_model=ParserHealthReport,
    status_code=status.HTTP_200_OK,
)
async def supported_formats() -> ParserHealthReport:
    """List the document formats this build can route to a parser.

    Pipeline stage: ``health`` — returns the static set of formats the
    pipeline's :class:`DocumentFormat` enum advertises as routable. Actual parser
    registration happens inside the pipeline runtime (out of scope for the API
    surface in this PR), so the per-format ``available`` flag here reflects only
    whether the format is recognised by the router, not whether any specific
    parser binary is installed in the current environment.

    Async response structure: a :class:`ParserHealthReport` payload with a
    top-level ``healthy`` boolean (true when the format enum is non-empty) and a
    ``formats`` list of :class:`ParserHealth` entries.
    """
    entries = [
        ParserHealth(format=fmt.value, available=True, parsers=[])
        for fmt in DocumentFormat
        if fmt is not DocumentFormat.UNKNOWN
    ]
    return ParserHealthReport(healthy=bool(entries), formats=entries)
