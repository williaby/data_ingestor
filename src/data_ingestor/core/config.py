"""Configuration settings for the data ingestion pipeline."""

from pathlib import Path
from typing import Any, cast

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="DATA_INGESTOR_",
        case_sensitive=False,
        extra="ignore",
    )

    # Application settings
    app_name: str = "Data Ingestor"
    version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"

    # Storage settings
    storage_backend: str = "filesystem"  # filesystem, s3, azure
    storage_path: Path = Field(default=Path("./data/processed"))
    database_url: str = "postgresql://localhost/data_ingestor"

    # #CRITICAL: Security: Database credentials in connection string
    # #VERIFY: Must use encrypted secrets or environment variables, not hardcoded

    # Redis settings for task queue
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None

    # Processing settings
    max_workers: int = 4
    max_file_size_mb: int = 500
    enable_gpu: bool = True  # For OCR and transcription

    # #CRITICAL: GPU Availability: Assumes GPU is available when enabled
    # #VERIFY: Must detect GPU availability and fallback to CPU

    # Parser settings
    pdf_parser_priority: list[str] = Field(default=["marker", "pymupdf4llm", "pymupdf"])
    enable_ocr: bool = True
    ocr_languages: list[str] = Field(default=["eng"])

    # PDF Resolution Pre-processing (Phase 1c)
    enable_pdf_upscaling: bool = True  # Enable automatic upscaling for low-res PDFs
    pdf_min_dpi: int = 300  # Minimum acceptable DPI (trigger upscaling below this)
    pdf_target_dpi: int = 300  # Target DPI for upscaling
    pdf_upscale_algorithm: str = "lanczos"  # Algorithm: lanczos, bicubic, inter_cubic
    pdf_preserve_original_on_error: bool = True  # Keep original if upscaling fails

    # #CRITICAL: Resolution Settings: Values impact OCR quality and processing time
    # #VERIFY: Monitor performance impact and adjust thresholds as needed

    # Chunking settings
    chunking_strategy: str = "element_based"  # element_based, token_based
    chunk_size: int = 1000  # tokens
    chunk_overlap: int = 200  # tokens
    preserve_tables: bool = True

    # Quality settings
    quality_threshold: float = Field(default=0.70, ge=0.0, le=1.0)
    enable_quality_checks: bool = True
    flag_for_review_threshold: float = Field(default=0.85, ge=0.0, le=1.0)

    # API settings
    api_host: str = "0.0.0.0"  # noqa: S104
    api_port: int = 8000
    api_workers: int = 1

    # Rate limiting for web scraping
    web_scraping_delay: float = 1.0  # seconds between requests
    respect_robots_txt: bool = True

    # #CRITICAL: Rate Limiting: Web scraping must respect robots.txt and rate limits
    # #VERIFY: Implement proper delay and directive compliance to avoid bans

    # OpenRouter API rate limiting
    openrouter_tier: str = "paid"  # "free" (< $10 credits) or "paid" ($10+ credits)
    openrouter_rpm_limit: int = 20  # Requests per minute (OpenRouter limit for :free models)
    openrouter_daily_limit_free: int = 50  # Daily limit for free tier
    openrouter_daily_limit_paid: int = 1000  # Daily limit for paid tier (with $10+ credits)
    openrouter_enable_rate_limiting: bool = True  # Enable rate limiting (recommended)
    openrouter_rate_limit_timeout: float = 300.0  # Max wait time in seconds (5 min default)

    # #CRITICAL: API Rate Limiting: OpenRouter enforces 20 RPM for :free models
    # #VERIFY: Must implement rate limiting to avoid 429 errors and API blocks

    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090

    @field_validator("storage_path", mode="before")
    @classmethod
    def ensure_storage_path_exists(cls, v: str | Path) -> Path:
        """Ensure storage path exists."""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @field_validator("celery_broker_url", mode="before")
    @classmethod
    def set_celery_broker_default(cls, v: str | None, info: Any) -> str:
        """Set celery broker URL to redis_url if not provided."""
        if v is None:
            return cast(str, info.data.get("redis_url", "redis://localhost:6379/0"))
        return v

    @field_validator("celery_result_backend", mode="before")
    @classmethod
    def set_celery_result_backend_default(cls, v: str | None, info: Any) -> str:
        """Set celery result backend to redis_url if not provided."""
        if v is None:
            return cast(str, info.data.get("redis_url", "redis://localhost:6379/0"))
        return v

    def get_parser_config(self, parser_name: str) -> dict[str, Any]:
        """Get configuration for a specific parser.

        Args:
            parser_name: Name of the parser

        Returns:
            Configuration dictionary for the parser
        """
        return {
            "max_file_size_mb": self.max_file_size_mb,
            "enable_gpu": self.enable_gpu,
            "enable_ocr": self.enable_ocr,
            "ocr_languages": self.ocr_languages,
            "debug": self.debug,
        }
