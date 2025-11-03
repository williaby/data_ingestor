"""Command-line interface for document processing."""

import json
import logging
import sys
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from data_ingestor.chunking.token_chunker import TokenChunker
from data_ingestor.core.config import Settings
from data_ingestor.core.models import DocumentFormat
from data_ingestor.parsers.pdf_parser import MarkerParser, PyMuPDF4LLMParser, PyMuPDFParser
from data_ingestor.pipeline.router import DocumentRouter

console = Console()


def setup_logging(debug: bool = False) -> None:
    """Set up logging configuration.

    Args:
        debug: Enable debug logging
    """
    level = logging.DEBUG if debug else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.pass_context
def cli(ctx: click.Context, debug: bool) -> None:
    """Data Ingestor - RAG Data Ingestion Pipeline.

    Process documents (PDF, DOCX, Web, Video) into RAG-ready chunks.
    """
    setup_logging(debug)
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug
    ctx.obj["settings"] = Settings()


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option("--format", "-f", type=click.Choice(["json", "markdown", "text"]), default="json", help="Output format")
@click.option("--chunk-size", type=int, default=1000, help="Chunk size in tokens")
@click.option("--chunk-overlap", type=int, default=200, help="Chunk overlap in tokens")
@click.pass_context
def process(
    ctx: click.Context,
    file_path: str,
    output: str | None,
    format: str,
    chunk_size: int,
    chunk_overlap: int,
) -> None:
    """Process a single document.

    Example:
        data-ingestor process document.pdf --output output.json
    """
    settings: Settings = ctx.obj["settings"]

    try:
        # Initialize router
        router = DocumentRouter(settings)

        # Register PDF parsers (in priority order: Marker → PyMuPDF4LLM → PyMuPDF)
        marker_parser = MarkerParser(settings.get_parser_config("marker"))
        pymupdf4llm_parser = PyMuPDF4LLMParser(settings.get_parser_config("pymupdf4llm"))
        pymupdf_parser = PyMuPDFParser(settings.get_parser_config("pymupdf"))

        # Marker has priority 10 (highest quality, optional)
        router.parser_registry.register(marker_parser, [DocumentFormat.PDF])
        # PyMuPDF4LLM has priority 100 (LLM-optimized, reliable)
        router.parser_registry.register(pymupdf4llm_parser, [DocumentFormat.PDF])
        # PyMuPDF has priority 100 (fast fallback)
        router.parser_registry.register(pymupdf_parser, [DocumentFormat.PDF])

        console.print(f"[bold blue]Processing document:[/bold blue] {file_path}")

        # Process document
        document, result = router.process_document(source_path=file_path)

        if not result.success:
            console.print(f"[bold red]Error:[/bold red] {result.error_message}")
            sys.exit(1)

        console.print(f"[bold green]✓[/bold green] Parsed with {result.parser_name}")
        console.print(f"[dim]Processing time: {result.processing_time:.2f}s[/dim]")
        console.print(f"[dim]Elements extracted: {len(document.elements)}[/dim]")

        # Chunk document
        if document.elements:
            console.print(f"\n[bold blue]Chunking document...[/bold blue]")
            chunker = TokenChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            chunks = chunker.chunk_document(document)
            document.chunks = chunks

            console.print(f"[bold green]✓[/bold green] Created {len(chunks)} chunks")

            # Display chunk statistics
            if chunks:
                total_tokens = sum(c.token_count or 0 for c in chunks)
                avg_tokens = total_tokens / len(chunks) if chunks else 0
                console.print(f"[dim]Total tokens: {total_tokens}[/dim]")
                console.print(f"[dim]Average tokens per chunk: {avg_tokens:.0f}[/dim]")

        # Output results
        if output:
            output_path = Path(output)
            if format == "json":
                _output_json(document, output_path)
            elif format == "markdown":
                _output_markdown(document, output_path)
            else:
                _output_text(document, output_path)

            console.print(f"\n[bold green]✓[/bold green] Output saved to {output}")
        else:
            # Display preview
            _display_preview(document)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if ctx.obj["debug"]:
            console.print_exception()
        sys.exit(1)


@cli.command()
@click.pass_context
def health(ctx: click.Context) -> None:
    """Check health of all parsers."""
    settings: Settings = ctx.obj["settings"]

    router = DocumentRouter(settings)

    # Register all PDF parsers
    marker_parser = MarkerParser(settings.get_parser_config("marker"))
    pymupdf4llm_parser = PyMuPDF4LLMParser(settings.get_parser_config("pymupdf4llm"))
    pymupdf_parser = PyMuPDFParser(settings.get_parser_config("pymupdf"))

    router.parser_registry.register(marker_parser, [DocumentFormat.PDF])
    router.parser_registry.register(pymupdf4llm_parser, [DocumentFormat.PDF])
    router.parser_registry.register(pymupdf_parser, [DocumentFormat.PDF])

    # Get health status
    health_status = router.parser_registry.health_check()

    # Display results
    table = Table(title="Parser Health Status")
    table.add_column("Format", style="cyan")
    table.add_column("Parser", style="magenta")
    table.add_column("Status", style="green")

    for format_name, parsers in health_status.items():
        for parser in parsers:
            status = "✓ Healthy" if parser["healthy"] else "✗ Unhealthy"
            status_style = "green" if parser["healthy"] else "red"
            error = parser.get("error", "")

            table.add_row(
                format_name,
                parser["name"],
                f"[{status_style}]{status}[/{status_style}]",
            )

            if error:
                console.print(f"  [red]Error:[/red] {error}")

    console.print(table)


def _output_json(document: Any, output_path: Path) -> None:  # noqa: ANN401
    """Output document as JSON.

    Args:
        document: Document to output
        output_path: Output file path
    """
    data = {
        "document_id": document.document_id,
        "source_path": document.source_path,
        "format": document.format.value,
        "status": document.status.value,
        "metadata": document.metadata,
        "elements": [
            {
                "type": e.element_type.value,
                "content": e.content,
                "page_number": e.page_number,
                "metadata": e.metadata,
            }
            for e in document.elements
        ],
        "chunks": [
            {
                "chunk_id": c.chunk_id,
                "content": c.content,
                "token_count": c.token_count,
                "metadata": c.metadata,
            }
            for c in document.chunks
        ],
    }

    with output_path.open("w") as f:
        json.dump(data, f, indent=2)


def _output_markdown(document: Any, output_path: Path) -> None:  # noqa: ANN401
    """Output document as Markdown.

    Args:
        document: Document to output
        output_path: Output file path
    """
    lines: list[str] = []

    # Add title
    lines.append(f"# {document.metadata.get('title', 'Document')}\n")

    # Add metadata
    lines.append("## Metadata\n")
    for key, value in document.metadata.items():
        lines.append(f"- **{key}**: {value}")
    lines.append("")

    # Add content
    lines.append("## Content\n")
    for element in document.elements:
        if element.element_type.value == "title":
            lines.append(f"# {element.content}\n")
        elif element.element_type.value == "heading":
            lines.append(f"## {element.content}\n")
        else:
            lines.append(f"{element.content}\n")

    with output_path.open("w") as f:
        f.write("\n".join(lines))


def _output_text(document: Any, output_path: Path) -> None:  # noqa: ANN401
    """Output document as plain text.

    Args:
        document: Document to output
        output_path: Output file path
    """
    lines = [element.content for element in document.elements]

    with output_path.open("w") as f:
        f.write("\n\n".join(lines))


def _display_preview(document: Any) -> None:  # noqa: ANN401
    """Display document preview in console.

    Args:
        document: Document to display
    """
    console.print("\n[bold]Document Preview:[/bold]\n")

    # Show first few elements
    for i, element in enumerate(document.elements[:10]):
        element_type = element.element_type.value
        content = element.content[:100] + "..." if len(element.content) > 100 else element.content

        console.print(f"[cyan]{element_type}[/cyan]: {content}")

    if len(document.elements) > 10:
        console.print(f"\n[dim]... and {len(document.elements) - 10} more elements[/dim]")

    # Show chunk preview
    if document.chunks:
        console.print("\n[bold]Chunk Preview:[/bold]\n")
        for i, chunk in enumerate(document.chunks[:3]):
            content = chunk.content[:150] + "..." if len(chunk.content) > 150 else chunk.content
            console.print(f"[yellow]Chunk {i + 1}[/yellow] ({chunk.token_count} tokens):")
            console.print(f"  {content}\n")

        if len(document.chunks) > 3:
            console.print(f"[dim]... and {len(document.chunks) - 3} more chunks[/dim]")


if __name__ == "__main__":
    cli()
