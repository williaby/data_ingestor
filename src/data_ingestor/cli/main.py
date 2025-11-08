"""Command-line interface for document processing."""

import logging
import os
import sys
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from data_ingestor.chunking import ByTitleChunker, TokenChunker
from data_ingestor.core.config import Settings
from data_ingestor.core.models import DocumentFormat
from data_ingestor.export.exporter import DocumentExporter, OutputFormat
from data_ingestor.parsers.pdf_parser import MarkerParser, PyMuPDF4LLMParser, PyMuPDFParser
from data_ingestor.pipeline.router import DocumentRouter
from data_ingestor.benchmarking import BenchmarkOrchestrator, BenchmarkReporter


def setup_logging(debug: bool = False) -> Console:
    """Set up logging configuration and return console instance.

    Args:
        debug: Enable debug logging

    Returns:
        Console instance for this CLI invocation
    """
    # Create console per invocation for thread-safety
    console = Console()
    level = logging.DEBUG if debug else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )

    return console


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.pass_context
def cli(ctx: click.Context, debug: bool) -> None:
    """Data Ingestor - RAG Data Ingestion Pipeline.

    Process documents (PDF, DOCX, Web, Video) into RAG-ready chunks.
    """
    console = setup_logging(debug)
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug
    ctx.obj["settings"] = Settings()
    ctx.obj["console"] = console


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
    console: Console = ctx.obj["console"]
    exporter = DocumentExporter()

    try:
        # Initialize router
        router = DocumentRouter(settings)

        # Register PDF parsers (in priority order: Marker → PyMuPDF4LLM → PyMuPDF)
        # Skip Marker parser in test environment to avoid slow PyTorch loading
        skip_marker = os.getenv("SKIP_MARKER_PARSER", "").lower() in ("1", "true", "yes")

        if not skip_marker:
            try:
                marker_parser = MarkerParser(settings.get_parser_config("marker"))
                # Marker has priority 10 (highest quality, optional)
                router.parser_registry.register(marker_parser, [DocumentFormat.PDF])
            except Exception:
                # Marker is optional, gracefully skip if unavailable
                pass

        pymupdf4llm_parser = PyMuPDF4LLMParser(settings.get_parser_config("pymupdf4llm"))
        pymupdf_parser = PyMuPDFParser(settings.get_parser_config("pymupdf"))

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
            console.print("\n[bold blue]Chunking document...[/bold blue]")

            # Select chunking strategy
            chunker: ByTitleChunker | TokenChunker
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
            _display_preview(document, console)

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
    console: Console = ctx.obj["console"]

    router = DocumentRouter(settings)

    # Register all PDF parsers
    # Skip Marker parser in test environment to avoid slow PyTorch loading
    skip_marker = os.getenv("SKIP_MARKER_PARSER", "").lower() in ("1", "true", "yes")

    if not skip_marker:
        try:
            marker_parser = MarkerParser(settings.get_parser_config("marker"))
            router.parser_registry.register(marker_parser, [DocumentFormat.PDF])
        except Exception:
            # Marker is optional, gracefully skip if unavailable
            pass

    pymupdf4llm_parser = PyMuPDF4LLMParser(settings.get_parser_config("pymupdf4llm"))
    pymupdf_parser = PyMuPDFParser(settings.get_parser_config("pymupdf"))

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


@cli.command()
@click.option(
    "--datasets",
    "-d",
    multiple=True,
    help="Datasets to benchmark (doclaynet only in Phase 1b). Default: doclaynet",
)
@click.option(
    "--parsers",
    "-p",
    multiple=True,
    help="Parsers to test (pymupdf, pymupdf4llm). Default: all",
)
@click.option(
    "--workers",
    "-w",
    type=int,
    default=4,
    help="Number of parallel workers",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output JSON file (default: timestamp-based)",
)
@click.option(
    "--output-dir",
    type=click.Path(),
    default="results",
    help="Output directory for results",
)
@click.pass_context
def benchmark(
    ctx: click.Context,
    datasets: tuple[str, ...],
    parsers: tuple[str, ...],
    workers: int,
    output: str | None,
    output_dir: str,
) -> None:
    """Run comprehensive benchmark on DocLayNet dataset (Phase 1b baseline).

    Examples:
        # Run benchmark on DocLayNet
        data-ingestor benchmark

        # Benchmark with specific dataset
        data-ingestor benchmark -d doclaynet

        # Test specific parsers
        data-ingestor benchmark -p pymupdf -p pymupdf4llm

        # Custom configuration
        data-ingestor benchmark -d doclaynet -p pymupdf -w 8 -o baseline.json
    """
    console: Console = ctx.obj["console"]

    try:
        console.print("\n[bold blue]🚀 Starting Benchmark Run[/bold blue]\n")

        # Convert tuples to lists
        dataset_list = list(datasets) if datasets else None
        parser_list = list(parsers) if parsers else None

        # Initialize orchestrator
        orchestrator = BenchmarkOrchestrator(
            datasets=dataset_list,
            parsers=parser_list,
            workers=workers,
            output_dir=output_dir,
        )

        console.print(f"[cyan]Datasets:[/cyan] {', '.join(orchestrator.config.datasets)}")
        console.print(f"[cyan]Parsers:[/cyan] {', '.join(orchestrator.config.parsers)}")
        console.print(f"[cyan]Workers:[/cyan] {workers}\n")

        # Run benchmark
        with console.status("[bold green]Running benchmarks..."):
            results = orchestrator.run()

        # Save results
        output_file = output if output else None
        saved_path = orchestrator.save_results(results, output_file)

        # Display summary
        console.print("\n[bold green]✓ Benchmark Complete[/bold green]\n")

        overall = results.get("overall", {})
        console.print(f"[cyan]Total Documents:[/cyan] {overall.get('total_documents', 0)}")
        console.print(f"[cyan]Success Rate:[/cyan] {overall.get('success_rate', 0):.1%}")
        console.print(f"[cyan]Throughput:[/cyan] {overall.get('throughput_docs_per_hour', 0):.1f} docs/hr")
        console.print(f"[cyan]Total Time:[/cyan] {overall.get('total_time', 0)/60:.1f} minutes")
        console.print(f"\n[cyan]Results saved to:[/cyan] {saved_path}")

        console.print("\n[dim]Generate reports with:[/dim]")
        console.print(f"[dim]  data-ingestor benchmark-report {saved_path}[/dim]")

    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        if ctx.obj["debug"]:
            console.print_exception()
        sys.exit(1)


@cli.command()
@click.argument("results_file", type=click.Path(exists=True))
@click.option(
    "--format",
    "-f",
    type=click.Choice(["html", "json", "csv", "all"]),
    default="html",
    help="Report format",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file path (auto-generated if not specified)",
)
@click.pass_context
def benchmark_report(
    ctx: click.Context,
    results_file: str,
    format: str,
    output: str | None,
) -> None:
    """Generate reports from benchmark results.

    Examples:
        # Generate HTML report
        data-ingestor benchmark-report results/baseline.json

        # Generate all formats
        data-ingestor benchmark-report results/baseline.json --format all

        # Custom output location
        data-ingestor benchmark-report results/baseline.json -o reports/my_report.html
    """
    console: Console = ctx.obj["console"]

    try:
        console.print(f"\n[bold blue]📊 Generating Report[/bold blue]\n")
        console.print(f"[cyan]Input:[/cyan] {results_file}")
        console.print(f"[cyan]Format:[/cyan] {format}\n")

        # Load results
        import json

        with open(results_file) as f:
            results = json.load(f)

        # Initialize reporter
        reporter = BenchmarkReporter(results)

        # Determine output paths
        results_path = Path(results_file)
        base_name = results_path.stem

        generated_files = []

        if format in ["html", "all"]:
            html_output = output if output and format == "html" else f"reports/{base_name}.html"
            html_path = reporter.generate_html(html_output)
            generated_files.append(("HTML", html_path))

        if format in ["json", "all"]:
            json_output = output if output and format == "json" else f"reports/{base_name}_report.json"
            json_path = reporter.generate_json(json_output)
            generated_files.append(("JSON", json_path))

        if format in ["csv", "all"]:
            csv_output = output if output and format == "csv" else f"reports/{base_name}_metrics.csv"
            csv_path = reporter.generate_csv(csv_output)
            generated_files.append(("CSV", csv_path))

        # Display results
        console.print("[bold green]✓ Reports Generated[/bold green]\n")

        for format_name, file_path in generated_files:
            console.print(f"[cyan]{format_name}:[/cyan] {file_path}")

        if "html" in [f[0] for f in generated_files]:
            html_file = [f[1] for f in generated_files if f[0] == "HTML"][0]
            console.print(f"\n[dim]Open in browser:[/dim] file://{Path(html_file).absolute()}")

    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        if ctx.obj["debug"]:
            console.print_exception()
        sys.exit(1)


def _display_preview(document: Any, console: Console) -> None:
    """Display document preview in console.

    Args:
        document: Document to display
        console: Console instance for output
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
