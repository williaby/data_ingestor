"""Document export service for JSON, Markdown, and other formats."""

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from data_ingestor.core.models import Chunk, Document, DocumentElement, ElementType


class OutputFormat(str, Enum):
    """Supported output formats."""

    JSON = "json"
    MARKDOWN = "markdown"
    BOTH = "both"
    TEXT = "text"
    HTML = "html"


class DocumentExporter:
    """Export documents to various formats with metadata preservation.

    Supports JSON, Markdown, and dual-format export inspired by Unstructured.io.
    """

    def __init__(self) -> None:
        """Initialize the document exporter."""
        pass

    def export(
        self,
        document: Document,
        format: OutputFormat,  # noqa: A002
        output_path: str | Path | None = None,
    ) -> dict[str, Any] | str | tuple[dict[str, Any], str]:
        """Export document in specified format.

        Args:
            document: Document to export
            format: Output format
            output_path: Optional output file path (for BOTH format, will create .json and .md)

        Returns:
            Exported data in requested format

        Raises:
            ValueError: If format is unsupported
        """
        if format == OutputFormat.JSON:
            result = self.to_json(document)
            if output_path:
                self._write_json(result, Path(output_path))
            return result

        elif format == OutputFormat.MARKDOWN:
            result = self.to_markdown(document)
            if output_path:
                self._write_markdown(result, Path(output_path))
            return result

        elif format == OutputFormat.BOTH:
            json_data = self.to_json(document)
            markdown_data = self.to_markdown(document)

            if output_path:
                base_path = Path(output_path).with_suffix("")
                self._write_json(json_data, base_path.with_suffix(".json"))
                self._write_markdown(markdown_data, base_path.with_suffix(".md"))

            return json_data, markdown_data

        elif format == OutputFormat.TEXT:
            result = self.to_text(document)
            if output_path:
                Path(output_path).write_text(result, encoding="utf-8")
            return result

        else:
            msg = f"Unsupported format: {format}"
            raise ValueError(msg)

    def to_json(self, document: Document) -> dict[str, Any]:
        """Export document as JSON with full metadata.

        Args:
            document: Document to export

        Returns:
            JSON-serializable dictionary
        """
        return {
            "document_id": document.document_id,
            "source_path": document.source_path,
            "source_url": document.source_url,
            "format": document.format.value,
            "status": document.status.value,
            "created_at": document.created_at.isoformat(),
            "updated_at": document.updated_at.isoformat(),
            "metadata": document.metadata,
            "parser_used": document.parser_used,
            "processing_time": document.processing_time,
            "elements": [self._element_to_dict(e) for e in document.elements],
            "chunks": [self._chunk_to_dict(c) for c in document.chunks],
            "quality_metrics": (
                {
                    "overall_score": document.quality_metrics.overall_score,
                    "quality_level": document.quality_metrics.quality_level.value,
                    "text_extraction_score": document.quality_metrics.text_extraction_score,
                    "structure_preservation_score": document.quality_metrics.structure_preservation_score,
                    "table_accuracy_score": document.quality_metrics.table_accuracy_score,
                    "metadata_completeness_score": document.quality_metrics.metadata_completeness_score,
                    "failed_checks": document.quality_metrics.failed_checks,
                    "warnings": document.quality_metrics.warnings,
                }
                if document.quality_metrics
                else None
            ),
        }

    def to_markdown(self, document: Document, include_chunks: bool = False) -> str:
        """Export document as Markdown with YAML front matter.

        Preserves document structure, metadata, and formatting in LLM-friendly format.

        Args:
            document: Document to export
            include_chunks: Whether to include chunk information

        Returns:
            Markdown-formatted string with YAML front matter
        """
        lines: list[str] = []

        # Add YAML front matter
        lines.append("---")
        front_matter = {
            "document_id": document.document_id,
            "source": document.source_path or document.source_url,
            "format": document.format.value,
            "status": document.status.value,
            "created_at": document.created_at.isoformat(),
            "parser_used": document.parser_used,
            "processing_time": document.processing_time,
            "total_elements": len(document.elements),
            "total_chunks": len(document.chunks),
        }

        # Add document metadata to front matter
        if document.metadata:
            front_matter["metadata"] = document.metadata

        # Add quality metrics if available
        if document.quality_metrics:
            front_matter["quality"] = {
                "score": document.quality_metrics.overall_score,
                "level": document.quality_metrics.quality_level.value,
            }

        lines.append(yaml.dump(front_matter, default_flow_style=False, sort_keys=False))
        lines.append("---\n")

        # Add document content
        for element in document.elements:
            lines.append(self._element_to_markdown(element))

        # Optionally add chunk information
        if include_chunks and document.chunks:
            lines.append("\n---\n")
            lines.append("## Document Chunks\n")
            for i, chunk in enumerate(document.chunks, 1):
                lines.append(f"### Chunk {i}\n")
                lines.append(f"**Tokens**: {chunk.token_count}\n")
                if chunk.start_page and chunk.end_page:
                    lines.append(f"**Pages**: {chunk.start_page}-{chunk.end_page}\n")
                lines.append(f"\n{chunk.content}\n")

        return "\n".join(lines)

    def to_text(self, document: Document) -> str:
        """Export document as plain text.

        Args:
            document: Document to export

        Returns:
            Plain text content
        """
        return "\n\n".join(element.content for element in document.elements)

    def _element_to_dict(self, element: DocumentElement) -> dict[str, Any]:
        """Convert element to dictionary.

        Args:
            element: Element to convert

        Returns:
            Dictionary representation
        """
        return {
            "element_id": element.metadata.element_id,
            "type": element.element_type.value,
            "content": element.content,
            "metadata": {
                "page_number": element.metadata.page_number,
                "coordinates": element.metadata.coordinates,
                "parent_id": element.metadata.parent_id,
                "category_depth": element.metadata.category_depth,
                "text_as_html": element.metadata.text_as_html,
                "languages": element.metadata.languages,
                "emphasized_text_contents": element.metadata.emphasized_text_contents,
                "emphasized_text_tags": element.metadata.emphasized_text_tags,
                "detection_class_prob": element.metadata.detection_class_prob,
                "extra": element.metadata.extra,
            },
        }

    def _chunk_to_dict(self, chunk: Chunk) -> dict[str, Any]:
        """Convert chunk to dictionary.

        Args:
            chunk: Chunk to convert

        Returns:
            Dictionary representation
        """
        return {
            "chunk_id": chunk.chunk_id,
            "content": chunk.content,
            "token_count": chunk.token_count,
            "char_count": chunk.char_count,
            "start_page": chunk.start_page,
            "end_page": chunk.end_page,
            "metadata": chunk.metadata,
            "element_count": len(chunk.elements),
        }

    def _element_to_markdown(self, element: DocumentElement) -> str:
        """Convert element to markdown representation.

        Args:
            element: Element to convert

        Returns:
            Markdown-formatted string
        """
        element_type = element.element_type

        # Handle titles and headings
        if element_type in (ElementType.TITLE, ElementType.HEADING):
            depth = element.metadata.category_depth or 1
            heading_prefix = "#" * min(depth, 6)
            return f"{heading_prefix} {element.content}\n"

        # Handle list items
        elif element_type == ElementType.LIST_ITEM:
            return f"- {element.content}\n"

        # Handle tables
        elif element_type == ElementType.TABLE:
            if element.metadata.text_as_html:
                # Try to preserve table structure
                return f"{element.content}\n"
            else:
                return f"\n{element.content}\n"

        # Handle code snippets
        elif element_type in (ElementType.CODE_SNIPPET, ElementType.CODE):
            return f"```\n{element.content}\n```\n"

        # Handle formulas
        elif element_type == ElementType.FORMULA:
            return f"$${element.content}$$\n"

        # Handle images
        elif element_type == ElementType.IMAGE:
            caption = element.content or "Image"
            return f"![{caption}](image)\n"

        # Handle figure captions
        elif element_type in (ElementType.FIGURE_CAPTION, ElementType.CAPTION):
            return f"*{element.content}*\n"

        # Handle emphasized text
        elif element.metadata.emphasized_text_contents:
            # Content has emphasis, try to preserve it
            content = element.content
            for emphasized_text in element.metadata.emphasized_text_contents:
                if emphasized_text in content:
                    content = content.replace(emphasized_text, f"**{emphasized_text}**")
            return f"{content}\n"

        # Default: narrative text and paragraphs
        else:
            return f"{element.content}\n"

    def _write_json(self, data: dict[str, Any], path: Path) -> None:
        """Write JSON data to file.

        Args:
            data: JSON data
            path: Output file path
        """
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _write_markdown(self, content: str, path: Path) -> None:
        """Write markdown content to file.

        Args:
            content: Markdown content
            path: Output file path
        """
        path.write_text(content, encoding="utf-8")
