"""Process-local state for the API layer (in-memory job tracker and start time).

This module deliberately avoids touching pipeline business logic or storage backends.
It holds only ephemeral API-layer state used to satisfy status/health queries.
"""

from __future__ import annotations

import time
from threading import Lock

from data_ingestor.api.models import JobState, JobStatus

_PROCESS_START_MONO: float = time.monotonic()
_JOBS: dict[str, JobStatus] = {}
_LOCK = Lock()


def uptime_seconds() -> float:
    """Return seconds elapsed since the API process started."""
    return max(0.0, time.monotonic() - _PROCESS_START_MONO)


def record_job(job: JobStatus) -> None:
    """Insert a job snapshot into the in-memory tracker."""
    with _LOCK:
        _JOBS[job.job_id] = job


def get_job(job_id: str) -> JobStatus | None:
    """Return the tracked job, or None if no such id exists."""
    with _LOCK:
        return _JOBS.get(job_id)


def counts_by_state() -> dict[JobState, int]:
    """Return job counts grouped by lifecycle state."""
    counts: dict[JobState, int] = {state: 0 for state in JobState}
    with _LOCK:
        for job in _JOBS.values():
            counts[job.state] = counts.get(job.state, 0) + 1
    return counts


def total_jobs() -> int:
    """Return the total number of jobs tracked since process start."""
    with _LOCK:
        return len(_JOBS)
