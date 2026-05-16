"""Ingest-stage routes: accept documents and report per-job status."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from data_ingestor.api import state
from data_ingestor.api.models import (
    ErrorResponse,
    IngestAccepted,
    IngestRequest,
    JobState,
    JobStatus,
)

router = APIRouter(tags=["ingest"])


@router.post(
    "/ingest",
    summary="Submit a document for ingestion",
    response_model=IngestAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        422: {"description": "Validation error", "model": ErrorResponse},
        503: {"description": "No parser available for the resolved document format",
              "model": ErrorResponse},
    },
)
async def submit_ingest(request: IngestRequest) -> IngestAccepted:
    """Accept a document into the ingestion pipeline.

    Pipeline stage: ``ingest`` — enqueues the request for asynchronous processing by the
    pipeline's :class:`DocumentRouter`. This endpoint records a job entry in the
    in-memory tracker and returns immediately; actual parsing, chunking, and export are
    performed by the pipeline workers.

    Async response structure: a :class:`IngestAccepted` payload with the server-issued
    ``job_id``, the initial ``state`` (``"queued"``), the ``submitted_at`` UTC timestamp,
    and a ``poll_url`` the client can ``GET`` for status updates.
    """
    accepted = IngestAccepted(state=JobState.QUEUED, poll_url="")
    accepted.poll_url = f"/ingest/{accepted.job_id}/status"
    state.record_job(
        JobStatus(
            job_id=accepted.job_id,
            state=accepted.state,
            submitted_at=accepted.submitted_at,
        )
    )
    return accepted


@router.get(
    "/ingest/{job_id}/status",
    summary="Get ingestion job status",
    response_model=JobStatus,
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "Unknown job id", "model": ErrorResponse}},
)
async def job_status(job_id: str) -> JobStatus:
    """Return the lifecycle snapshot for a previously submitted ingestion job.

    Pipeline stage: ``ingest`` — read-only view over the in-memory job tracker; does not
    re-trigger parsing or touch storage.

    Async response structure: a :class:`JobStatus` payload with ``job_id``, current
    ``state``, ``submitted_at`` / ``started_at`` / ``completed_at`` timestamps,
    ``parser_used`` (when known), and an optional ``error`` string for failed jobs.
    """
    job = state.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Unknown job id: {job_id}")
    return job
