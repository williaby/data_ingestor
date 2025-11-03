"""Core data models for document processing."""

from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class DocumentFormat(str, Enum):
    """Supported document formats."""

    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"
    VIDEO = "video"
    AUDIO = "audio"
    UNKNOWN = "unknown"


class ElementType(str, Enum):
    """Types of document elements."""

    TITLE = "title"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    LIST = "list"
    IMAGE = "image"
    FORMULA = "formula"
    CODE = "code"
    CAPTION = "caption"
    FOOTNOTE = "footnote"
    REFERENCE = "reference"
    METADATA = "metadata"
    UNKNOWN = "unknown"


class QualityLevel(str, Enum):
    """Quality assessment levels."""

    EXCELLENT = "excellent"  # >= 95%
    GOOD = "good"  # 85-94%
    MARGINAL = "marginal"  # 70-84%
    POOR = "poor"  # < 70%


class ProcessingStatus(str, Enum):
    """Document processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REQUIRES_REVIEW = "requires_review"


class DocumentElement(BaseModel):
    """A single element extracted from a document."""

    element_type: ElementType
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    bbox: tuple[float, float, float, float] | None = None  # x0, y0, x1, y1
    page_number: int | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    # #CRITICAL: Data Integrity: Assumes content is valid UTF-8 string
    # #VERIFY: Must validate and sanitize content to prevent encoding errors
    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate that content is non-empty after stripping."""
        if not v or not v.strip():
            msg = "Element content cannot be empty"
            raise ValueError(msg)
        return v


class Chunk(BaseModel):
    """A chunk of processed document content."""

    chunk_id: str = Field(default_factory=lambda: str(uuid4()))
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    elements: list[DocumentElement] = Field(default_factory=list)
    token_count: int | None = None
    char_count: int = Field(default=0)
    start_page: int | None = None
    end_page: int | None = None

    def model_post_init(self, __context: Any) -> None:  # noqa: ANN401
        """Calculate character count if not provided."""
        if self.char_count == 0:
            self.char_count = len(self.content)


class QualityMetrics(BaseModel):
    """Quality assessment metrics for processed documents."""

    overall_score: float = Field(ge=0.0, le=1.0)
    text_extraction_score: float | None = Field(default=None, ge=0.0, le=1.0)
    structure_preservation_score: float | None = Field(default=None, ge=0.0, le=1.0)
    table_accuracy_score: float | None = Field(default=None, ge=0.0, le=1.0)
    metadata_completeness_score: float | None = Field(default=None, ge=0.0, le=1.0)
    quality_level: QualityLevel
    failed_checks: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @field_validator("quality_level", mode="before")
    @classmethod
    def calculate_quality_level(cls, v: QualityLevel | None, info: Any) -> QualityLevel:  # noqa: ANN401
        """Calculate quality level from overall score if not provided."""
        if v is not None:
            return v

        overall_score = info.data.get("overall_score", 0.0)
        if overall_score >= 0.95:
            return QualityLevel.EXCELLENT
        if overall_score >= 0.85:
            return QualityLevel.GOOD
        if overall_score >= 0.70:
            return QualityLevel.MARGINAL
        return QualityLevel.POOR


class ParserResult(BaseModel):
    """Result from a document parser."""

    success: bool
    elements: list[DocumentElement] = Field(default_factory=list)
    raw_content: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    parser_name: str
    processing_time: float  # seconds
    error_message: str | None = None
    warnings: list[str] = Field(default_factory=list)

    # #ASSUME: Parser Reliability: Assumes parser success flag accurately reflects extraction quality
    # #VERIFY: Should validate element count and content length match expectations


class Document(BaseModel):
    """A document to be processed."""

    document_id: str = Field(default_factory=lambda: str(uuid4()))
    source_path: str | None = None
    source_url: str | None = None
    format: DocumentFormat
    status: ProcessingStatus = ProcessingStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Processing results
    elements: list[DocumentElement] = Field(default_factory=list)
    chunks: list[Chunk] = Field(default_factory=list)
    quality_metrics: QualityMetrics | None = None

    # Parser information
    parser_used: str | None = None
    processing_time: float | None = None

    # #CRITICAL: External Resources: Assumes source_path or source_url is valid and accessible
    # #VERIFY: Must validate file existence and accessibility before processing
    @field_validator("source_path", mode="before")
    @classmethod
    def validate_source_path(cls, v: str | None) -> str | None:
        """Validate that source path exists if provided."""
        if v is not None:
            path = Path(v)
            if not path.exists():
                msg = f"Source path does not exist: {v}"
                raise ValueError(msg)
        return v

    def update_status(self, status: ProcessingStatus) -> None:
        """Update document status and timestamp."""
        self.status = status
        self.updated_at = datetime.now(UTC)
