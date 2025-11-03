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

from data_ingestor.chunking import ByTitleChunker, ChunkingStrategy, TokenChunker
from data_ingestor.core.config import Settings
from data_ingestor.core.models import DocumentFormat
from data_ingestor.export.exporter import DocumentExporter, OutputFormat
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
@click.option("--output", "-o", type=click.Path(), help="Output file path (for 'both' format, creates .json and .md)")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["json", "markdown", "both", "text"]),
    default="json",
    help="Output format (both exports JSON and Markdown)",
)
@click.option("--chunk-size", type=int, default=1000, help="Chunk size in tokens")
@click.option("--chunk-overlap", type=int, default=200, help="Chunk overlap in tokens")
@click.option(
    "--chunking-strategy",
    type=click.Choice(["basic", "by_title"]),
    default="basic",
    help="Chunking strategy (basic: token-based, by_title: section-aware)",
)
@click.option("--combine-under", type=int, help="Combine sections under N characters (by_title only)")
@click.option("--include-chunks", is_flag=True, help="Include chunks in markdown output")
@click.pass_context
def process(
    ctx: click.Context,
    file_path: str,
    output: str | None,
    format: str,
    chunk_size: int,
    chunk_overlap: int,
    chunking_strategy: str,
    combine_under: int | None,
    include_chunks: bool,
) -> None:
    """Process a single document.

    Examples:
        # Export as JSON
        data-ingestor process document.pdf --output output.json

        # Export as Markdown
        data-ingestor process document.pdf --format markdown --output output.md

        # Export both JSON and Markdown
        data-ingestor process document.pdf --format both --output document
    """
    settings: Settings = ctx.obj["settings"]
    exporter = DocumentExporter()

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

            # Select chunking strategy
            if chunking_strategy == "by_title":
                chunker = ByTitleChunker(
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    combine_text_under_n_chars=combine_under,
                )
                console.print("[dim]Using by_title strategy (section-aware)[/dim]")
            else:
                chunker = TokenChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
                console.print("[dim]Using basic strategy (token-based)[/dim]")

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
            output_format = OutputFormat(format)

            # Handle special case for include_chunks in markdown
            if format == "markdown" and include_chunks:
                markdown_content = exporter.to_markdown(document, include_chunks=True)
                Path(output).write_text(markdown_content, encoding="utf-8")
                console.print(f"\n[bold green]✓[/bold green] Markdown output saved to {output}")
            else:
                # Use standard export method
                exporter.export(document, output_format, output)

                if format == "both":
                    base_name = Path(output).stem
                    console.print(f"\n[bold green]✓[/bold green] JSON output saved to {base_name}.json")
                    console.print(f"[bold green]✓[/bold green] Markdown output saved to {base_name}.md")
                else:
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
