"""Hybrid chunker checks that need the Hugging Face hub."""

import pytest

from data_ingestor.chunking import load_tokenizer

pytestmark = pytest.mark.integration


def test_real_qwen_tokenizer_loads_and_counts() -> None:
    """The default tokenizer is the Qwen3-Embedding one; skip when the hub is unreachable."""
    try:
        tokenizer = load_tokenizer("Qwen/Qwen3-Embedding-0.6B", max_tokens=512)
    except OSError:
        pytest.skip("Hugging Face hub not reachable")
    else:
        assert type(tokenizer.get_tokenizer()).__name__.startswith("Qwen")
        assert tokenizer.count_tokens("hello world") >= 2
        assert tokenizer.get_max_tokens() == 512
