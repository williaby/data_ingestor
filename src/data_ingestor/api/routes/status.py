"""Status-stage routes: aggregate pipeline status metrics."""

from __future__ import annotations

from fastapi import APIRouter, status

from data_ingestor.api import state
from data_ingestor.api.models import JobState, PipelineStatus

router = APIRouter(tags=["status"])


@router.get(
    "/status",
    summary="Pipeline status snapshot",
    response_model=PipelineStatus,
    status_code=status.HTTP_200_OK,
)
async def pipeline_status() -> PipelineStatus:
    """Return an aggregate snapshot of pipeline activity.

    Pipeline stage: ``status`` — read-only view over the API process's in-memory job
    tracker. Does not invoke parser or storage code.

    Async response structure: a :class:`PipelineStatus` payload with ``total_jobs`` and
    per-state counters (``queued``, ``running``, ``completed``, ``failed``) plus
    ``uptime_seconds`` since process start.
    """
    counts = state.counts_by_state()
    return PipelineStatus(
        total_jobs=sum(counts.values()),
        queued=counts.get(JobState.QUEUED, 0),
        running=counts.get(JobState.RUNNING, 0),
        completed=counts.get(JobState.COMPLETED, 0),
        failed=counts.get(JobState.FAILED, 0),
        uptime_seconds=state.uptime_seconds(),
    )
