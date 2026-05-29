"""Comprehensive tests for configuration settings."""

from pathlib import Path

import pytest

from data_ingestor.core.config import Settings


class TestSettingsInitialization:
    """Tests for Settings initialization."""

    def test_default_initialization(self) -> None:
        """Test Settings with default values."""
        settings = Settings()

        assert settings.app_name == "Data Ingestor"
        assert settings.version == "0.1.0"
        assert settings.debug is False
        assert settings.log_level == "INFO"

    def test_custom_app_name(self) -> None:
        """Test custom app name."""
        settings = Settings(app_name="Custom App")
        assert settings.app_name == "Custom App"

    def test_custom_version(self) -> None:
        """Test custom version."""
        settings = Settings(version="1.0.0")
        assert settings.version == "1.0.0"

    def test_debug_mode(self) -> None:
        """Test debug mode setting."""
        settings = Settings(debug=True)
        assert settings.debug is True

    def test_log_level_custom(self) -> None:
        """Test custom log level."""
        settings = Settings(log_level="DEBUG")
        assert settings.log_level == "DEBUG"


class TestStorageSettings:
    """Tests for storage configuration."""

    def test_default_storage_backend(self) -> None:
        """Test default storage backend."""
        settings = Settings()
        assert settings.storage_backend == "filesystem"

    def test_custom_storage_backend(self) -> None:
        """Test custom storage backend."""
        settings = Settings(storage_backend="s3")
        assert settings.storage_backend == "s3"

    def test_storage_path_default(self, tmp_path: Path, monkeypatch) -> None:
        """Test default storage path."""
        # Change to tmp directory to avoid creating dirs in project
        monkeypatch.chdir(tmp_path)
        settings = Settings()
        assert settings.storage_path is not None

    def test_storage_path_custom(self, tmp_path: Path) -> None:
        """Test custom storage path."""
        custom_path = tmp_path / "custom_storage"
        settings = Settings(storage_path=str(custom_path))
        assert settings.storage_path == custom_path
        assert custom_path.exists()  # Should be created

    def test_storage_path_creates_directory(self, tmp_path: Path) -> None:
        """Test that storage path is created if it doesn't exist."""
        new_path = tmp_path / "new_storage_dir"
        assert not new_path.exists()

        settings = Settings(storage_path=str(new_path))
        assert new_path.exists()
        assert new_path.is_dir()

    def test_database_url_default(self) -> None:
        """Test default database URL."""
        settings = Settings()
        assert settings.database_url == "postgresql://localhost/data_ingestor"

    def test_database_url_custom(self) -> None:
        """Test custom database URL."""
        settings = Settings(database_url="postgresql://host:5432/mydb")
        assert settings.database_url == "postgresql://host:5432/mydb"


class TestRedisSettings:
    """Tests for Redis and Celery configuration."""

    def test_redis_url_default(self) -> None:
        """Test default Redis URL."""
        settings = Settings()
        assert settings.redis_url == "redis://localhost:6379/0"

    def test_redis_url_custom(self) -> None:
        """Test custom Redis URL."""
        settings = Settings(redis_url="redis://custom-host:6380/1")
        assert settings.redis_url == "redis://custom-host:6380/1"

    def test_celery_broker_url_defaults_to_redis(self) -> None:
        """Test that celery_broker_url defaults to redis_url."""
        settings = Settings(redis_url="redis://myhost:6379/0")
        assert settings.celery_broker_url == "redis://myhost:6379/0"

    def test_celery_broker_url_custom(self) -> None:
        """Test custom celery broker URL."""
        settings = Settings(
            redis_url="redis://localhost:6379/0",
            celery_broker_url="redis://broker:6379/1",
        )
        assert settings.celery_broker_url == "redis://broker:6379/1"

    def test_celery_result_backend_defaults_to_redis(self) -> None:
        """Test that celery_result_backend defaults to redis_url."""
        settings = Settings(redis_url="redis://myhost:6379/0")
        assert settings.celery_result_backend == "redis://myhost:6379/0"

    def test_celery_result_backend_custom(self) -> None:
        """Test custom celery result backend."""
        settings = Settings(
            redis_url="redis://localhost:6379/0",
            celery_result_backend="redis://backend:6379/2",
        )
        assert settings.celery_result_backend == "redis://backend:6379/2"


class TestProcessingSettings:
    """Tests for processing configuration."""

    def test_max_workers_default(self) -> None:
        """Test default max workers."""
        settings = Settings()
        assert settings.max_workers == 4

    def test_max_workers_custom(self) -> None:
        """Test custom max workers."""
        settings = Settings(max_workers=8)
        assert settings.max_workers == 8

    def test_max_file_size_mb_default(self) -> None:
        """Test default max file size."""
        settings = Settings()
        assert settings.max_file_size_mb == 500

    def test_max_file_size_mb_custom(self) -> None:
        """Test custom max file size."""
        settings = Settings(max_file_size_mb=1000)
        assert settings.max_file_size_mb == 1000

    def test_enable_gpu_default(self) -> None:
        """Test GPU enabled by default."""
        settings = Settings()
        assert settings.enable_gpu is True

    def test_enable_gpu_disabled(self) -> None:
        """Test GPU can be disabled."""
        settings = Settings(enable_gpu=False)
        assert settings.enable_gpu is False


class TestParserSettings:
    """Tests for parser configuration."""

    def test_pdf_parser_priority_default(self) -> None:
        """Test default PDF parser priority."""
        settings = Settings()
        assert settings.pdf_parser_priority == ["marker", "pymupdf4llm", "pymupdf"]

    def test_pdf_parser_priority_custom(self) -> None:
        """Test custom PDF parser priority."""
        custom_priority = ["pymupdf", "marker"]
        settings = Settings(pdf_parser_priority=custom_priority)
        assert settings.pdf_parser_priority == custom_priority

    def test_enable_ocr_default(self) -> None:
        """Test OCR enabled by default."""
        settings = Settings()
        assert settings.enable_ocr is True

    def test_enable_ocr_disabled(self) -> None:
        """Test OCR can be disabled."""
        settings = Settings(enable_ocr=False)
        assert settings.enable_ocr is False

    def test_ocr_languages_default(self) -> None:
        """Test default OCR languages."""
        settings = Settings()
        assert settings.ocr_languages == ["eng"]

    def test_ocr_languages_custom(self) -> None:
        """Test custom OCR languages."""
        languages = ["eng", "spa", "fra"]
        settings = Settings(ocr_languages=languages)
        assert settings.ocr_languages == languages


class TestChunkingSettings:
    """Tests for chunking configuration."""

    def test_chunking_strategy_default(self) -> None:
        """Test default chunking strategy."""
        settings = Settings()
        assert settings.chunking_strategy == "element_based"

    def test_chunking_strategy_custom(self) -> None:
        """Test custom chunking strategy."""
        settings = Settings(chunking_strategy="token_based")
        assert settings.chunking_strategy == "token_based"

    def test_chunk_size_default(self) -> None:
        """Test default chunk size."""
        settings = Settings()
        assert settings.chunk_size == 1000

    def test_chunk_size_custom(self) -> None:
        """Test custom chunk size."""
        settings = Settings(chunk_size=500)
        assert settings.chunk_size == 500

    def test_chunk_overlap_default(self) -> None:
        """Test default chunk overlap."""
        settings = Settings()
        assert settings.chunk_overlap == 200

    def test_chunk_overlap_custom(self) -> None:
        """Test custom chunk overlap."""
        settings = Settings(chunk_overlap=100)
        assert settings.chunk_overlap == 100

    def test_preserve_tables_default(self) -> None:
        """Test tables preserved by default."""
        settings = Settings()
        assert settings.preserve_tables is True

    def test_preserve_tables_disabled(self) -> None:
        """Test tables preservation can be disabled."""
        settings = Settings(preserve_tables=False)
        assert settings.preserve_tables is False


class TestQualitySettings:
    """Tests for quality configuration."""

    def test_quality_threshold_default(self) -> None:
        """Test default quality threshold."""
        settings = Settings()
        assert settings.quality_threshold == 0.70

    def test_quality_threshold_custom(self) -> None:
        """Test custom quality threshold."""
        settings = Settings(quality_threshold=0.85)
        assert settings.quality_threshold == 0.85

    def test_quality_threshold_bounds(self) -> None:
        """Test quality threshold validation bounds."""
        # Valid values
        Settings(quality_threshold=0.0)
        Settings(quality_threshold=1.0)
        Settings(quality_threshold=0.5)

        # Invalid values should raise validation error
        with pytest.raises(Exception):  # Pydantic validation error
            Settings(quality_threshold=-0.1)

        with pytest.raises(Exception):
            Settings(quality_threshold=1.1)

    def test_enable_quality_checks_default(self) -> None:
        """Test quality checks enabled by default."""
        settings = Settings()
        assert settings.enable_quality_checks is True

    def test_enable_quality_checks_disabled(self) -> None:
        """Test quality checks can be disabled."""
        settings = Settings(enable_quality_checks=False)
        assert settings.enable_quality_checks is False

    def test_flag_for_review_threshold_default(self) -> None:
        """Test default review threshold."""
        settings = Settings()
        assert settings.flag_for_review_threshold == 0.85

    def test_flag_for_review_threshold_custom(self) -> None:
        """Test custom review threshold."""
        settings = Settings(flag_for_review_threshold=0.90)
        assert settings.flag_for_review_threshold == 0.90


class TestAPISettings:
    """Tests for API configuration."""

    def test_api_host_default(self) -> None:
        """Test default API host."""
        settings = Settings()
        assert settings.api_host == "0.0.0.0"

    def test_api_host_custom(self) -> None:
        """Test custom API host."""
        settings = Settings(api_host="127.0.0.1")
        assert settings.api_host == "127.0.0.1"

    def test_api_port_default(self) -> None:
        """Test default API port."""
        settings = Settings()
        assert settings.api_port == 8000

    def test_api_port_custom(self) -> None:
        """Test custom API port."""
        settings = Settings(api_port=8080)
        assert settings.api_port == 8080

    def test_api_workers_default(self) -> None:
        """Test default API workers."""
        settings = Settings()
        assert settings.api_workers == 1

    def test_api_workers_custom(self) -> None:
        """Test custom API workers."""
        settings = Settings(api_workers=4)
        assert settings.api_workers == 4


class TestWebScrapingSettings:
    """Tests for web scraping configuration."""

    def test_web_scraping_delay_default(self) -> None:
        """Test default web scraping delay."""
        settings = Settings()
        assert settings.web_scraping_delay == 1.0

    def test_web_scraping_delay_custom(self) -> None:
        """Test custom web scraping delay."""
        settings = Settings(web_scraping_delay=2.5)
        assert settings.web_scraping_delay == 2.5

    def test_respect_robots_txt_default(self) -> None:
        """Test robots.txt respected by default."""
        settings = Settings()
        assert settings.respect_robots_txt is True

    def test_respect_robots_txt_disabled(self) -> None:
        """Test robots.txt respect can be disabled."""
        settings = Settings(respect_robots_txt=False)
        assert settings.respect_robots_txt is False


class TestMonitoringSettings:
    """Tests for monitoring configuration."""

    def test_enable_metrics_default(self) -> None:
        """Test metrics enabled by default."""
        settings = Settings()
        assert settings.enable_metrics is True

    def test_enable_metrics_disabled(self) -> None:
        """Test metrics can be disabled."""
        settings = Settings(enable_metrics=False)
        assert settings.enable_metrics is False

    def test_metrics_port_default(self) -> None:
        """Test default metrics port."""
        settings = Settings()
        assert settings.metrics_port == 9090

    def test_metrics_port_custom(self) -> None:
        """Test custom metrics port."""
        settings = Settings(metrics_port=9091)
        assert settings.metrics_port == 9091


class TestGetParserConfig:
    """Tests for get_parser_config method."""

    def test_get_parser_config_basic(self) -> None:
        """Test getting parser configuration."""
        settings = Settings()
        config = settings.get_parser_config("TestParser")

        assert isinstance(config, dict)
        assert "max_file_size_mb" in config
        assert "enable_gpu" in config
        assert "enable_ocr" in config
        assert "ocr_languages" in config
        assert "debug" in config

    def test_get_parser_config_values(self) -> None:
        """Test parser config contains correct values."""
        settings = Settings(
            max_file_size_mb=200,
            enable_gpu=False,
            enable_ocr=True,
            ocr_languages=["eng", "spa"],
            debug=True,
        )
        config = settings.get_parser_config("TestParser")

        assert config["max_file_size_mb"] == 200
        assert config["enable_gpu"] is False
        assert config["enable_ocr"] is True
        assert config["ocr_languages"] == ["eng", "spa"]
        assert config["debug"] is True

    def test_get_parser_config_different_parsers(self) -> None:
        """Test that config is same for different parser names."""
        settings = Settings()
        config1 = settings.get_parser_config("Parser1")
        config2 = settings.get_parser_config("Parser2")

        # Should return same config regardless of parser name
        assert config1 == config2


class TestEnvironmentVariables:
    """Tests for environment variable loading."""

    def test_env_prefix(self, monkeypatch) -> None:
        """Test environment variable prefix."""
        monkeypatch.setenv("DATA_INGESTOR_DEBUG", "true")
        settings = Settings()
        assert settings.debug is True

    def test_case_insensitive(self, monkeypatch) -> None:
        """Test case-insensitive environment variables."""
        monkeypatch.setenv("DATA_INGESTOR_LOG_LEVEL", "WARNING")
        settings = Settings()
        assert settings.log_level == "WARNING"

    def test_multiple_env_vars(self, monkeypatch) -> None:
        """Test multiple environment variables."""
        monkeypatch.setenv("DATA_INGESTOR_DEBUG", "true")
        monkeypatch.setenv("DATA_INGESTOR_MAX_WORKERS", "8")
        monkeypatch.setenv("DATA_INGESTOR_CHUNK_SIZE", "2000")

        settings = Settings()
        assert settings.debug is True
        assert settings.max_workers == 8
        assert settings.chunk_size == 2000


class TestEdgeCases:
    """Tests for edge cases and validation."""

    def test_empty_ocr_languages(self) -> None:
        """Test empty OCR languages list."""
        settings = Settings(ocr_languages=[])
        assert settings.ocr_languages == []

    def test_empty_pdf_parser_priority(self) -> None:
        """Test empty PDF parser priority list."""
        settings = Settings(pdf_parser_priority=[])
        assert settings.pdf_parser_priority == []

    def test_zero_chunk_size(self) -> None:
        """Test zero chunk size."""
        settings = Settings(chunk_size=0)
        assert settings.chunk_size == 0

    def test_negative_max_workers(self) -> None:
        """Test negative max workers (should be allowed by Pydantic)."""
        settings = Settings(max_workers=-1)
        assert settings.max_workers == -1

    def test_very_large_chunk_size(self) -> None:
        """Test very large chunk size."""
        settings = Settings(chunk_size=1000000)
        assert settings.chunk_size == 1000000
