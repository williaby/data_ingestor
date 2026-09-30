"""Marker LLM mode must not be able to send document text off the machine."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from data_ingestor.core.exceptions import ConfigurationError
from data_ingestor.parsers.pdf_parser import MarkerParser
from data_ingestor.utils.llm_endpoint import is_loopback_url, require_local_llm_endpoint

LOCAL = "http://127.0.0.1:8081/v1"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("MARKER_USE_LLM", "MARKER_LLM_BASE_URL", "OPENROUTER_API_KEY"):
        monkeypatch.delenv(name, raising=False)


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:8081/v1",
        "http://127.0.0.1:8081/v1",
        "http://127.3.4.5/v1",
        "http://[::1]:8081/v1",
        "https://localhost/v1",
    ],
)
def test_loopback_urls_are_accepted(url: str) -> None:
    assert is_loopback_url(url)
    require_local_llm_endpoint(url)


@pytest.mark.parametrize(
    "url",
    [
        None,
        "",
        "https://openrouter.ai/api/v1",
        "https://api.example.com/v1",
        "http://203.0.113.5:8080",
        "http://198.51.100.20:8080",
        "http://0.0.0.0:8080",
        "http://127.0.0.1@evil.example/v1",  # real host is evil.example
        "http://localhost.evil.example/v1",
        "http://127.0.0.1.evil.example/v1",
        "ftp://localhost/v1",
        "localhost:8081",
        "not a url",
    ],
)
def test_non_loopback_urls_are_refused(url: str | None) -> None:
    assert not is_loopback_url(url)
    with pytest.raises(ConfigurationError):
        require_local_llm_endpoint(url)


def test_llm_mode_with_remote_endpoint_refuses_to_start(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MARKER_USE_LLM", "true")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("MARKER_LLM_BASE_URL", "https://openrouter.ai/api/v1")
    with pytest.raises(ConfigurationError):
        MarkerParser()


def test_llm_mode_without_an_endpoint_refuses_to_start(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unset used to mean the hosted default; now it means refuse."""
    monkeypatch.setenv("MARKER_USE_LLM", "true")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    with pytest.raises(ConfigurationError):
        MarkerParser()


def test_llm_mode_with_local_endpoint_starts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MARKER_USE_LLM", "true")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("MARKER_LLM_BASE_URL", LOCAL)
    parser = MarkerParser()
    assert parser.use_llm is True
    assert parser.llm_base_url == LOCAL


def test_llm_off_starts_even_if_a_remote_endpoint_is_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MARKER_LLM_BASE_URL", "https://openrouter.ai/api/v1")
    parser = MarkerParser()
    assert parser.use_llm is False


def test_send_time_check_blocks_a_remote_endpoint_set_after_startup(tmp_path: pytest.TempPathFactory) -> None:
    """use_llm can be flipped after construction; the converter must still never be built."""
    parser = MarkerParser()
    parser.use_llm = True
    parser.llm_base_url = "https://openrouter.ai/api/v1"
    marker_modules = {
        "marker": MagicMock(),
        "marker.config": MagicMock(),
        "marker.config.parser": MagicMock(),
        "marker.converters": MagicMock(),
        "marker.converters.pdf": MagicMock(),
    }
    with patch.dict(sys.modules, marker_modules):
        with pytest.raises(ConfigurationError):
            parser._process_with_llm("doc.pdf", {}, {}, "some/model")
        marker_modules["marker.converters.pdf"].PdfConverter.assert_not_called()
        marker_modules["marker.config.parser"].ConfigParser.assert_not_called()


def test_local_endpoint_is_passed_to_marker_and_no_hosted_url_remains() -> None:
    parser = MarkerParser()
    parser.llm_base_url = LOCAL
    parser.openrouter_api_key = "test-key"
    config_parser_module = MagicMock()
    marker_modules = {
        "marker": MagicMock(),
        "marker.config": MagicMock(),
        "marker.config.parser": config_parser_module,
        "marker.converters": MagicMock(),
        "marker.converters.pdf": MagicMock(),
    }
    with patch.dict(sys.modules, marker_modules):
        parser._process_with_llm("doc.pdf", {}, {}, "some/model")
    (passed_config,) = config_parser_module.ConfigParser.call_args.args
    assert passed_config["openai_base_url"] == LOCAL


def test_no_hosted_llm_url_is_hardcoded_in_the_parser_module() -> None:
    import inspect

    import data_ingestor.parsers.pdf_parser as module

    assert "openrouter.ai" not in inspect.getsource(module)
