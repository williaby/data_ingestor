# Marker LLM Implementation Guide

## Overview

This guide provides step-by-step instructions for implementing LLM-enhanced PDF extraction in your data_ingestor project using Marker and OpenRouter.

## Prerequisites

- ✅ Marker PDF installed: `uv sync --extra advanced-pdf`
- ✅ OpenRouter API key from zen-mcp-server
- ✅ Python 3.11+
- ✅ Existing MarkerParser implementation

## Implementation Steps

### Step 1: Configuration Class

Create a new configuration class for Marker LLM settings.

**File**: `src/data_ingestor/core/config.py`

```python
from pydantic import BaseModel, Field
from typing import Optional


class MarkerLLMConfig(BaseModel):
    """Configuration for Marker LLM-enhanced extraction."""

    # Enable LLM enhancement
    use_llm: bool = Field(default=False, description="Enable LLM-enhanced extraction")

    # OpenRouter configuration
    openrouter_api_key: Optional[str] = Field(
        default=None,
        description="OpenRouter API key (from zen-mcp-server)",
    )
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        description="OpenRouter API base URL",
    )

    # Model selection
    llm_model: str = Field(
        default="google/gemini-2.5-flash",
        description="LLM model to use for enhancement",
    )
    fallback_model: Optional[str] = Field(
        default="meta-llama/llama-3.1-405b-instruct:free",
        description="Fallback model if primary fails",
    )

    # Enhancement options
    redo_inline_math: bool = Field(
        default=False,
        description="Use LLM for high-quality inline math conversion",
    )
    block_correction_prompt: Optional[str] = Field(
        default=None,
        description="Custom prompt for output correction",
    )

    # Complexity-based routing
    enable_complexity_routing: bool = Field(
        default=True,
        description="Automatically select model based on document complexity",
    )

    # Cost controls
    max_cost_per_document: Optional[float] = Field(
        default=None,
        description="Maximum cost per document (USD)",
    )
    daily_cost_limit: Optional[float] = Field(
        default=None,
        description="Daily cost limit (USD)",
    )

    class Config:
        env_prefix = "MARKER_"


# Load from environment
def load_marker_llm_config() -> MarkerLLMConfig:
    """Load Marker LLM configuration from environment."""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    return MarkerLLMConfig(
        use_llm=os.getenv("MARKER_USE_LLM", "false").lower() == "true",
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
        openrouter_base_url=os.getenv(
            "MARKER_OPENROUTER_BASE_URL",
            "https://openrouter.ai/api/v1",
        ),
        llm_model=os.getenv("MARKER_LLM_MODEL", "google/gemini-2.5-flash"),
        fallback_model=os.getenv(
            "MARKER_FALLBACK_MODEL",
            "meta-llama/llama-3.1-405b-instruct:free",
        ),
        redo_inline_math=os.getenv("MARKER_REDO_INLINE_MATH", "false").lower() == "true",
        block_correction_prompt=os.getenv("MARKER_BLOCK_CORRECTION_PROMPT"),
        enable_complexity_routing=os.getenv(
            "MARKER_ENABLE_COMPLEXITY_ROUTING",
            "true",
        ).lower() == "true",
        max_cost_per_document=float(cost)
        if (cost := os.getenv("MARKER_MAX_COST_PER_DOCUMENT"))
        else None,
        daily_cost_limit=float(limit)
        if (limit := os.getenv("MARKER_DAILY_COST_LIMIT"))
        else None,
    )
```

### Step 2: Document Complexity Classifier

Create a classifier to determine document complexity for model selection.

**File**: `src/data_ingestor/utils/document_classifier.py`

```python
"""Document complexity classification for optimal model selection."""

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class DocumentComplexity(str, Enum):
    """Document complexity levels."""

    SIMPLE = "simple"  # Plain text, few elements
    MODERATE = "moderate"  # Some tables/formulas
    COMPLEX = "complex"  # Complex layouts, many tables/formulas
    IMAGE_HEAVY = "image_heavy"  # Heavy image content


@dataclass
class ComplexityAnalysis:
    """Analysis of document complexity."""

    complexity: DocumentComplexity
    page_count: int
    table_count: int
    formula_count: int
    image_count: int
    has_multi_column: bool
    confidence: float
    reasoning: str


def analyze_pdf_complexity(pdf_path: str) -> ComplexityAnalysis:
    """Analyze PDF complexity to guide model selection.

    Args:
        pdf_path: Path to PDF file

    Returns:
        ComplexityAnalysis with classification and metrics
    """
    try:
        doc = fitz.open(pdf_path)

        # Extract metrics
        page_count = len(doc)
        table_count = 0
        formula_count = 0
        image_count = 0
        has_multi_column = False

        for page in doc:
            # Count images
            image_count += len(page.get_images())

            # Analyze text blocks for tables and multi-column
            blocks = page.get_text("dict")["blocks"]

            # Simple heuristics for table detection
            for block in blocks:
                if block["type"] == 0:  # Text block
                    # Check for table-like patterns
                    text = ""
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text += span.get("text", "")

                    # Count table indicators
                    if "|" in text or text.count("\t") > 3:
                        table_count += 1

                    # Count formula indicators
                    if "$" in text or "=" in text or "∫" in text:
                        formula_count += 1

            # Multi-column detection (simplified)
            if len(blocks) > 2:
                # Check if blocks are side-by-side
                x_positions = [b["bbox"][0] for b in blocks if b["type"] == 0]
                if len(set(round(x / 50) for x in x_positions)) > 1:
                    has_multi_column = True

        doc.close()

        # Classify complexity
        complexity, confidence, reasoning = _classify_complexity(
            page_count,
            table_count,
            formula_count,
            image_count,
            has_multi_column,
        )

        return ComplexityAnalysis(
            complexity=complexity,
            page_count=page_count,
            table_count=table_count,
            formula_count=formula_count,
            image_count=image_count,
            has_multi_column=has_multi_column,
            confidence=confidence,
            reasoning=reasoning,
        )

    except Exception as e:
        logger.error(f"Failed to analyze PDF complexity: {e}")
        # Default to moderate on error
        return ComplexityAnalysis(
            complexity=DocumentComplexity.MODERATE,
            page_count=0,
            table_count=0,
            formula_count=0,
            image_count=0,
            has_multi_column=False,
            confidence=0.5,
            reasoning=f"Failed to analyze: {e}",
        )


def _classify_complexity(
    page_count: int,
    table_count: int,
    formula_count: int,
    image_count: int,
    has_multi_column: bool,
) -> tuple[DocumentComplexity, float, str]:
    """Classify document complexity based on metrics.

    Returns:
        (complexity_level, confidence, reasoning)
    """
    # Image-heavy documents
    if image_count > page_count * 2:
        return (
            DocumentComplexity.IMAGE_HEAVY,
            0.9,
            f"High image density ({image_count} images / {page_count} pages)",
        )

    # Complex documents
    if (
        table_count > 5
        or formula_count > 10
        or has_multi_column
        or (table_count > 2 and formula_count > 5)
    ):
        return (
            DocumentComplexity.COMPLEX,
            0.85,
            f"Complex structure: {table_count} tables, {formula_count} formulas, "
            f"multi-column: {has_multi_column}",
        )

    # Moderate documents
    if table_count > 0 or formula_count > 0 or page_count > 10:
        return (
            DocumentComplexity.MODERATE,
            0.75,
            f"Moderate complexity: {table_count} tables, {formula_count} formulas",
        )

    # Simple documents
    return (
        DocumentComplexity.SIMPLE,
        0.8,
        f"Simple text document: {page_count} pages, minimal structure",
    )


def recommend_model(
    complexity: DocumentComplexity,
    budget_tier: str = "economy",
) -> str:
    """Recommend optimal model based on complexity and budget.

    Args:
        complexity: Document complexity level
        budget_tier: Budget tier (free, economy, value, premium)

    Returns:
        Recommended model identifier
    """
    recommendations = {
        DocumentComplexity.SIMPLE: {
            "free": "meta-llama/llama-3.1-405b-instruct:free",
            "economy": "google/gemini-2.5-flash",
            "value": "deepseek/deepseek-r1-0528",
            "premium": "openai/gpt-5",
        },
        DocumentComplexity.MODERATE: {
            "free": "qwen/qwen-2.5-coder-32b-instruct:free",
            "economy": "google/gemini-2.5-flash",
            "value": "deepseek/deepseek-r1-0528",
            "premium": "openai/gpt-5",
        },
        DocumentComplexity.COMPLEX: {
            "free": "deepseek/deepseek-r1-distill-llama-70b:free",
            "economy": "google/gemini-2.5-flash",
            "value": "deepseek/deepseek-r1-0528",
            "premium": "anthropic/claude-opus-4.1",
        },
        DocumentComplexity.IMAGE_HEAVY: {
            "free": "qwen/qwen2.5-vl-72b-instruct:free",
            "economy": "google/gemini-2.5-flash",
            "value": "google/gemini-2.5-pro",
            "premium": "anthropic/claude-opus-4.1",
        },
    }

    return recommendations[complexity][budget_tier]
```

### Step 3: Enhanced MarkerParser

Update the MarkerParser to support LLM enhancement.

**File**: `src/data_ingestor/parsers/pdf_parser.py` (add new class)

```python
class MarkerLLMParser(BaseParser):
    """PDF parser using Marker with LLM enhancement via OpenRouter.

    Provides high-quality extraction with:
    - LLM-enhanced table merging across pages
    - Improved inline math formatting
    - Form value extraction
    - Custom block correction prompts
    - Complexity-based model selection
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize Marker LLM parser.

        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        self.name = "MarkerLLMParser"
        self._marker_available = False
        self._gpu_available = False

        # Load LLM configuration
        from data_ingestor.core.config import load_marker_llm_config

        self.llm_config = load_marker_llm_config()

        # Validate OpenRouter API key
        if self.llm_config.use_llm and not self.llm_config.openrouter_api_key:
            logger.warning(
                "Marker LLM enabled but no OpenRouter API key found. "
                "Falling back to basic Marker."
            )
            self.llm_config.use_llm = False

        # Check Marker availability
        try:
            import marker  # noqa: F401

            self._marker_available = True

            # Check GPU
            try:
                import torch

                self._gpu_available = torch.cuda.is_available()
                logger.info(
                    f"Marker LLM: GPU {'available' if self._gpu_available else 'not available'}"
                )
            except ImportError:
                logger.info("Marker LLM: Running in CPU mode")

        except ImportError:
            logger.warning(
                "marker-pdf not installed. Install with: uv sync --extra advanced-pdf"
            )

        # Cost tracking
        self._daily_cost = 0.0
        self._last_reset = None

    def supports_format(self, document_format: DocumentFormat) -> bool:
        """Check if this parser supports PDF format.

        Args:
            document_format: Format to check

        Returns:
            True if PDF and Marker is available
        """
        return document_format == DocumentFormat.PDF and self._marker_available

    def parse(self, document: Document) -> ParserResult:
        """Parse PDF with LLM enhancement.

        Args:
            document: Document to parse

        Returns:
            ParserResult with extracted elements

        Raises:
            ParserError: If parsing fails
        """
        if not document.source_path:
            raise ParserError(
                message="Source path required for PDF parsing",
                parser_name=self.name,
            )

        if not self._marker_available:
            return ParserResult(
                success=False,
                parser_name=self.name,
                processing_time=0.0,
                error_message="marker-pdf not installed",
            )

        start_time = time.time()

        try:
            # Analyze document complexity
            from data_ingestor.utils.document_classifier import (
                analyze_pdf_complexity,
                recommend_model,
            )

            complexity_analysis = analyze_pdf_complexity(document.source_path)
            logger.info(
                f"Document complexity: {complexity_analysis.complexity} "
                f"(confidence: {complexity_analysis.confidence:.2f})"
            )
            logger.info(f"Reasoning: {complexity_analysis.reasoning}")

            # Select model based on complexity
            selected_model = self.llm_config.llm_model
            if self.llm_config.enable_complexity_routing:
                budget_tier = self._determine_budget_tier()
                recommended = recommend_model(complexity_analysis.complexity, budget_tier)
                selected_model = recommended
                logger.info(f"Selected model: {selected_model} (budget tier: {budget_tier})")

            # Load Marker models
            from marker.convert import convert_single_pdf
            from marker.models import load_all_models

            logger.info("Loading Marker models...")
            model_lst = load_all_models()

            # Configure LLM service
            llm_service_config = None
            if self.llm_config.use_llm:
                llm_service_config = {
                    "provider": "openai",  # OpenRouter is OpenAI-compatible
                    "api_key": self.llm_config.openrouter_api_key,
                    "base_url": self.llm_config.openrouter_base_url,
                    "model": selected_model,
                }

                # Add optional configurations
                if self.llm_config.block_correction_prompt:
                    llm_service_config["block_correction_prompt"] = (
                        self.llm_config.block_correction_prompt
                    )

                logger.info(f"LLM enhancement enabled with model: {selected_model}")

            # Convert PDF
            logger.info(f"Processing {Path(document.source_path).name} with Marker...")

            full_text, images, metadata = convert_single_pdf(
                document.source_path,
                model_lst,
                llm_config=llm_service_config,
                max_pages=self.config.get("max_pages"),
                langs=self.config.get("ocr_languages", ["English"]),
            )

            # Convert to elements
            elements = self._markdown_to_elements(full_text)

            # Track costs
            if self.llm_config.use_llm:
                estimated_cost = self._estimate_cost(
                    complexity_analysis.page_count,
                    selected_model,
                )
                self._track_cost(estimated_cost)
                logger.info(f"Estimated cost: ${estimated_cost:.4f}")

            # Enhanced metadata
            enhanced_metadata = {
                "page_count": metadata.get("pages", 0),
                "toc": metadata.get("toc", []),
                "languages": metadata.get("languages", []),
                "images_extracted": len(images),
                "marker_version": metadata.get("version", "unknown"),
                "gpu_used": self._gpu_available,
                "llm_enhanced": self.llm_config.use_llm,
                "llm_model": selected_model if self.llm_config.use_llm else None,
                "complexity": complexity_analysis.complexity,
                "complexity_metrics": {
                    "table_count": complexity_analysis.table_count,
                    "formula_count": complexity_analysis.formula_count,
                    "image_count": complexity_analysis.image_count,
                    "has_multi_column": complexity_analysis.has_multi_column,
                },
            }

            processing_time = time.time() - start_time
            logger.info(f"Marker LLM processing completed in {processing_time:.2f}s")

            return ParserResult(
                success=True,
                elements=elements,
                raw_content=full_text,
                metadata=enhanced_metadata,
                parser_name=self.name,
                processing_time=processing_time,
            )

        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Failed to parse PDF with Marker LLM: {e!s}"
            logger.error(error_msg)

            # Try fallback model
            if self.llm_config.fallback_model and self.llm_config.use_llm:
                logger.info(f"Retrying with fallback model: {self.llm_config.fallback_model}")
                return self._parse_with_fallback(document, start_time)

            return ParserResult(
                success=False,
                parser_name=self.name,
                processing_time=processing_time,
                error_message=error_msg,
            )

    def _markdown_to_elements(self, markdown: str) -> list[DocumentElement]:
        """Convert Marker's markdown to document elements.

        (Same implementation as MarkerParser)
        """
        # Reuse existing implementation
        pass

    def _determine_budget_tier(self) -> str:
        """Determine budget tier based on configuration.

        Returns:
            Budget tier name
        """
        # Check cost limits
        if self.llm_config.max_cost_per_document is not None:
            if self.llm_config.max_cost_per_document == 0:
                return "free"
            elif self.llm_config.max_cost_per_document < 0.01:
                return "economy"
            elif self.llm_config.max_cost_per_document < 0.05:
                return "value"
            else:
                return "premium"

        # Default to economy
        return "economy"

    def _estimate_cost(self, page_count: int, model: str) -> float:
        """Estimate cost for processing document.

        Args:
            page_count: Number of pages
            model: Model identifier

        Returns:
            Estimated cost in USD
        """
        # Cost per 10 pages (from analysis)
        cost_per_10_pages = {
            # Free models
            "meta-llama/llama-3.1-405b-instruct:free": 0.0,
            "deepseek/deepseek-r1-distill-llama-70b:free": 0.0,
            "qwen/qwen-2.5-coder-32b-instruct:free": 0.0,
            "qwen/qwen2.5-vl-72b-instruct:free": 0.0,
            # Economy models
            "google/gemini-2.5-flash": 0.0026,
            "qwen/qwen3-coder": 0.0070,
            "openai/o4-mini": 0.0053,
            # Value models
            "deepseek/deepseek-r1-0528": 0.0192,
            "openai/gpt-5-mini": 0.0175,
            # Premium models
            "google/gemini-2.5-pro": 0.0937,
            "openai/gpt-5": 0.0700,
            "anthropic/claude-opus-4.1": 0.6000,
        }

        cost_rate = cost_per_10_pages.get(model, 0.01)  # Default estimate
        return (page_count / 10) * cost_rate

    def _track_cost(self, cost: float) -> None:
        """Track daily cost and enforce limits.

        Args:
            cost: Cost to add
        """
        from datetime import datetime

        now = datetime.now()

        # Reset daily cost if new day
        if self._last_reset is None or self._last_reset.date() != now.date():
            self._daily_cost = 0.0
            self._last_reset = now

        self._daily_cost += cost

        # Check daily limit
        if (
            self.llm_config.daily_cost_limit is not None
            and self._daily_cost > self.llm_config.daily_cost_limit
        ):
            logger.warning(
                f"Daily cost limit exceeded: ${self._daily_cost:.2f} > "
                f"${self.llm_config.daily_cost_limit:.2f}. "
                "Disabling LLM enhancement for remaining documents today."
            )
            self.llm_config.use_llm = False

    def _parse_with_fallback(
        self,
        document: Document,
        original_start_time: float,
    ) -> ParserResult:
        """Parse with fallback model.

        Args:
            document: Document to parse
            original_start_time: Start time of original attempt

        Returns:
            ParserResult
        """
        try:
            # Save original model
            original_model = self.llm_config.llm_model

            # Switch to fallback
            self.llm_config.llm_model = self.llm_config.fallback_model

            # Retry
            result = self.parse(document)

            # Restore original model
            self.llm_config.llm_model = original_model

            return result

        except Exception as e:
            logger.error(f"Fallback parsing also failed: {e}")
            return ParserResult(
                success=False,
                parser_name=self.name,
                processing_time=time.time() - original_start_time,
                error_message=f"Both primary and fallback parsing failed: {e}",
            )

    def health_check(self) -> bool:
        """Check if Marker LLM is operational.

        Returns:
            True if operational
        """
        if not self._marker_available:
            return False

        # Check OpenRouter API key
        if self.llm_config.use_llm and not self.llm_config.openrouter_api_key:
            logger.warning("OpenRouter API key not configured")
            return False

        try:
            from marker.convert import convert_single_pdf  # noqa: F401
            from marker.models import load_all_models  # noqa: F401

            return True
        except Exception as e:
            logger.error(f"Marker LLM health check failed: {e}")
            return False
```

### Step 4: Environment Configuration

Update your `.env` file:

```bash
# ============================================
# Marker LLM Configuration
# ============================================

# Enable LLM-enhanced PDF extraction
MARKER_USE_LLM=true

# OpenRouter API Key (shared with zen-mcp-server)
# Get from: https://openrouter.ai/
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Default model for PDF extraction
# Recommended tiers:
#   Free: meta-llama/llama-3.1-405b-instruct:free
#   Economy: google/gemini-2.5-flash ($0.0026/10 pages)
#   Value: deepseek/deepseek-r1-0528 ($0.0192/10 pages)
#   Premium: openai/gpt-5 ($0.0700/10 pages)
MARKER_LLM_MODEL=google/gemini-2.5-flash

# Fallback model if primary fails
MARKER_FALLBACK_MODEL=meta-llama/llama-3.1-405b-instruct:free

# Enable complexity-based model routing
# Automatically selects optimal model based on document complexity
MARKER_ENABLE_COMPLEXITY_ROUTING=true

# High-quality math extraction (slower, more accurate)
MARKER_REDO_INLINE_MATH=false

# Custom block correction prompt (optional)
# Example: "Format tables as markdown with proper alignment"
MARKER_BLOCK_CORRECTION_PROMPT=

# Cost controls
MARKER_MAX_COST_PER_DOCUMENT=0.10  # USD
MARKER_DAILY_COST_LIMIT=10.00  # USD
```

### Step 5: Register Parser

Update parser registry to include new MarkerLLMParser.

**File**: `src/data_ingestor/parsers/__init__.py`

```python
"""Parser implementations."""

from data_ingestor.parsers.pdf_parser import (
    MarkerLLMParser,
    MarkerParser,
    PyMuPDF4LLMParser,
    PyMuPDFParser,
)

__all__ = [
    "PyMuPDFParser",
    "PyMuPDF4LLMParser",
    "MarkerParser",
    "MarkerLLMParser",  # Add new parser
]


def get_default_pdf_parser() -> str:
    """Get default PDF parser based on environment.

    Returns:
        Parser class name
    """
    import os

    # Check if LLM enhancement is enabled
    if os.getenv("MARKER_USE_LLM", "false").lower() == "true":
        return "MarkerLLMParser"

    # Check if Marker is available
    try:
        import marker  # noqa: F401

        return "MarkerParser"
    except ImportError:
        pass

    # Check if PyMuPDF4LLM is available
    try:
        import pymupdf4llm  # noqa: F401

        return "PyMuPDF4LLMParser"
    except ImportError:
        pass

    # Fallback to basic PyMuPDF
    return "PyMuPDFParser"
```

### Step 6: CLI Integration

Update CLI to support model selection.

**File**: `src/data_ingestor/cli/main.py`

```python
import click


@click.group()
def cli():
    """Data Ingestor CLI."""
    pass


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True))
@click.option(
    "--llm-model",
    type=str,
    default=None,
    help="LLM model to use (overrides MARKER_LLM_MODEL env var)",
)
@click.option(
    "--budget-tier",
    type=click.Choice(["free", "economy", "value", "premium"]),
    default="economy",
    help="Budget tier for automatic model selection",
)
@click.option(
    "--no-llm",
    is_flag=True,
    help="Disable LLM enhancement (use basic Marker)",
)
@click.option(
    "--analyze-only",
    is_flag=True,
    help="Only analyze document complexity without processing",
)
def process_pdf(pdf_path, llm_model, budget_tier, no_llm, analyze_only):
    """Process a PDF file with Marker LLM enhancement."""
    from data_ingestor.utils.document_classifier import (
        analyze_pdf_complexity,
        recommend_model,
    )
    from data_ingestor.parsers import MarkerLLMParser
    from data_ingestor.core.models import Document, DocumentFormat

    # Analyze complexity
    complexity = analyze_pdf_complexity(pdf_path)
    click.echo(f"\n📊 Document Complexity Analysis:")
    click.echo(f"  Complexity: {complexity.complexity}")
    click.echo(f"  Confidence: {complexity.confidence:.2%}")
    click.echo(f"  Reasoning: {complexity.reasoning}")
    click.echo(f"\n  Metrics:")
    click.echo(f"    Pages: {complexity.page_count}")
    click.echo(f"    Tables: {complexity.table_count}")
    click.echo(f"    Formulas: {complexity.formula_count}")
    click.echo(f"    Images: {complexity.image_count}")
    click.echo(f"    Multi-column: {complexity.has_multi_column}")

    # Recommend model
    recommended = recommend_model(complexity.complexity, budget_tier)
    click.echo(f"\n  Recommended model: {recommended}")

    if analyze_only:
        return

    # Configure parser
    config = {
        "use_llm": not no_llm,
    }
    if llm_model:
        config["llm_model"] = llm_model

    parser = MarkerLLMParser(config)

    # Process document
    doc = Document(
        source_path=pdf_path,
        format=DocumentFormat.PDF,
    )

    click.echo(f"\n🚀 Processing with Marker LLM...")
    result = parser.parse(doc)

    if result.success:
        click.echo(f"\n✅ Success!")
        click.echo(f"  Processing time: {result.processing_time:.2f}s")
        click.echo(f"  Elements extracted: {len(result.elements)}")
        if result.metadata.get("llm_enhanced"):
            click.echo(f"  LLM model used: {result.metadata.get('llm_model')}")
    else:
        click.echo(f"\n❌ Failed: {result.error_message}")


if __name__ == "__main__":
    cli()
```

## Testing

### Test Script

Create a test script to compare different models:

**File**: `scripts/test_marker_llm.py`

```python
"""Test script for Marker LLM integration."""

import logging
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data_ingestor.parsers import MarkerLLMParser
from data_ingestor.core.models import Document, DocumentFormat
from data_ingestor.utils.document_classifier import analyze_pdf_complexity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_model(pdf_path: str, model: str) -> dict:
    """Test a specific model on a PDF.

    Args:
        pdf_path: Path to PDF
        model: Model identifier

    Returns:
        Results dictionary
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing model: {model}")
    logger.info(f"{'='*60}")

    # Configure parser
    parser = MarkerLLMParser(config={"use_llm": True, "llm_model": model})

    # Create document
    doc = Document(source_path=pdf_path, format=DocumentFormat.PDF)

    # Parse
    result = parser.parse(doc)

    return {
        "model": model,
        "success": result.success,
        "processing_time": result.processing_time,
        "element_count": len(result.elements) if result.success else 0,
        "error": result.error_message if not result.success else None,
        "metadata": result.metadata if result.success else None,
    }


def main():
    """Run tests."""
    # Test PDF path
    pdf_path = os.getenv("TEST_PDF_PATH", "data/test_pdfs/sample.pdf")

    if not os.path.exists(pdf_path):
        logger.error(f"Test PDF not found: {pdf_path}")
        sys.exit(1)

    # Analyze complexity
    logger.info("Analyzing document complexity...")
    complexity = analyze_pdf_complexity(pdf_path)
    logger.info(f"Complexity: {complexity.complexity}")
    logger.info(f"Reasoning: {complexity.reasoning}")

    # Test models
    models_to_test = [
        # Free models
        "meta-llama/llama-3.1-405b-instruct:free",
        "qwen/qwen-2.5-coder-32b-instruct:free",
        # Economy models
        "google/gemini-2.5-flash",
        # Value models
        "deepseek/deepseek-r1-0528",
        # Premium models
        "openai/gpt-5",
    ]

    results = []
    for model in models_to_test:
        try:
            result = test_model(pdf_path, model)
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to test {model}: {e}")
            results.append(
                {
                    "model": model,
                    "success": False,
                    "error": str(e),
                }
            )

    # Print summary
    logger.info(f"\n{'='*60}")
    logger.info("SUMMARY")
    logger.info(f"{'='*60}")

    for result in results:
        logger.info(f"\nModel: {result['model']}")
        logger.info(f"  Success: {result['success']}")
        if result["success"]:
            logger.info(f"  Processing time: {result['processing_time']:.2f}s")
            logger.info(f"  Elements: {result['element_count']}")
        else:
            logger.info(f"  Error: {result['error']}")


if __name__ == "__main__":
    main()
```

Run the test:

```bash
# Set test PDF path
export TEST_PDF_PATH=data/test_pdfs/sample.pdf

# Set OpenRouter API key
export OPENROUTER_API_KEY=your_key_here

# Run test
uv run python scripts/test_marker_llm.py
```

## Next Steps

1. ✅ Review implementation code
2. ✅ Configure environment variables
3. ✅ Test with sample PDFs
4. ✅ Measure cost and quality
5. ✅ Deploy to production

## Troubleshooting

### Issue: "marker-pdf not installed"

```bash
uv sync --extra advanced-pdf
```

### Issue: "OpenRouter API key not found"

Check `.env` file has:
```bash
OPENROUTER_API_KEY=your_key_here
```

### Issue: "Model not found"

Verify model name matches zen-mcp-server configuration:
```bash
# Check available models
cat /home/byron/dev/zen-mcp-server/conf/openrouter_models.json
```

### Issue: High costs

Adjust budget controls in `.env`:
```bash
MARKER_MAX_COST_PER_DOCUMENT=0.01  # Lower limit
MARKER_DAILY_COST_LIMIT=1.00  # Lower daily limit
MARKER_LLM_MODEL=meta-llama/llama-3.1-405b-instruct:free  # Use free model
```

## References

- [Main Integration Proposal](MARKER_LLM_INTEGRATION.md)
- [Marker Documentation](https://github.com/VikParuchuri/marker)
- [OpenRouter API](https://openrouter.ai/docs)
- [Zen MCP Server](../../zen-mcp-server/README.md)
