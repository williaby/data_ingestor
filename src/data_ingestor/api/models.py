"""Pydantic request and response models for the Data Ingestor API."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from pathlib import PurePosixPath
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl, model_validator


class JobState(str, Enum):
    """Lifecycle state for an ingestion job."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class IngestRequest(BaseModel):
    """Request body for submitting a document to the ingestion pipeline.

    Exactly one of ``file_path`` or ``url`` must be supplied.
    """

    file_path: str | None = Field(
        default=None,
        description="Absolute or workspace-relative filesystem path to the source document.",
        examples=["/data/inbox/sample.pdf"],
    )
    url: HttpUrl | None = Field(
        default=None,
        description="HTTPS URL of the source document to be downloaded and processed.",
        examples=["https://example.com/sample.pdf"],
    )
    chunking_strategy: Literal["basic", "by_title"] = Field(
        default="basic",
        description="Chunking strategy identifier: 'basic' (token-based) or 'by_title' (section-aware).",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Caller-supplied metadata propagated onto the resulting Document record.",
    )

    @model_validator(mode="after")
    def _validate_source(self) -> IngestRequest:
        if bool(self.file_path) == bool(self.url):
            msg = "Provide exactly one of 'file_path' or 'url'."
            raise ValueError(msg)
        if self.file_path is not None:
            # Reject embedded NULs and any parent-directory traversal segment.
            if "\x00" in self.file_path:
                raise ValueError("file_path must not contain NUL bytes.")
            normalized = self.file_path.replace("\\", "/")
            if ".." in PurePosixPath(normalized).parts:
                raise ValueError(
                    "file_path must not contain parent-directory ('..') segments."
                )
        return self


class IngestAccepted(BaseModel):
    """Response returned when an ingestion job is accepted for asynchronous processing."""

    job_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Server-generated identifier used to poll job status.",
    )
    state: JobState = Field(
        default=JobState.QUEUED,
        description="Current lifecycle state of the job at acceptance time.",
    )
    submitted_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when the job was accepted by the API.",
    )
    poll_url: str = Field(
        description="Relative URL the client should poll for status updates.",
        examples=["/ingest/3f1c.../status"],
    )


class JobStatus(BaseModel):
    """Detailed status snapshot for a single ingestion job."""

    job_id: str = Field(description="Server-generated job identifier.")
    state: JobState = Field(description="Current lifecycle state of the job.")
    submitted_at: datetime = Field(description="UTC timestamp when the job was accepted.")
    started_at: datetime | None = Field(
        default=None, description="UTC timestamp when worker execution began."
    )
    completed_at: datetime | None = Field(
        default=None, description="UTC timestamp when the job terminated (succeeded or failed)."
    )
    parser_used: str | None = Field(
        default=None, description="Name of the parser that produced the result, if any."
    )
    error: str | None = Field(
        default=None, description="Error message if the job failed; null otherwise."
    )


class HealthStatus(BaseModel):
    """Liveness probe response for the API process."""

    status: Literal["ok"] = Field(
        default="ok",
        description="Literal 'ok' when the process is serving requests.",
    )
    version: str = Field(description="Application version identifier.")
    uptime_seconds: float = Field(
        ge=0.0, description="Seconds elapsed since the API process started."
    )


class ParserHealth(BaseModel):
    """Per-format parser health entry."""

    format: str = Field(description="Document format identifier (e.g. 'pdf', 'docx').")
    available: bool = Field(description="True when at least one parser is registered and healthy.")
    parsers: list[str] = Field(
        default_factory=list,
        description="Names of parsers registered for the format, ordered by priority.",
    )


class ParserHealthReport(BaseModel):
    """Aggregated parser-availability report across all supported formats."""

    healthy: bool = Field(description="True when every supported format has at least one parser.")
    formats: list[ParserHealth] = Field(
        default_factory=list, description="Per-format health entries."
    )


class PipelineStatus(BaseModel):
    """Aggregate runtime status for the ingestion pipeline."""

    total_jobs: int = Field(ge=0, description="Total jobs accepted since process start.")
    queued: int = Field(ge=0, description="Jobs currently in the QUEUED state.")
    running: int = Field(ge=0, description="Jobs currently in the RUNNING state.")
    completed: int = Field(ge=0, description="Jobs that finished successfully.")
    failed: int = Field(ge=0, description="Jobs that terminated with an error.")
    uptime_seconds: float = Field(ge=0.0, description="Seconds elapsed since process start.")


class ErrorResponse(BaseModel):
    """Generic error envelope returned for non-2xx responses."""

    detail: str = Field(description="Human-readable error description.")
