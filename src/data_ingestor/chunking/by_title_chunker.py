"""Section-aware chunking strategy that preserves title boundaries.

Based on Unstructured.io's by_title chunking strategy.
"""

import logging
from enum import Enum

import tiktoken

from data_ingestor.core.models import Chunk, Document, DocumentElement, ElementType

logger = logging.getLogger(__name__)


class ChunkingStrategy(str, Enum):
    """Supported chunking strategies."""

    BASIC = "basic"  # Token-based chunking
    BY_TITLE = "by_title"  # Section-aware chunking that preserves title boundaries


class ByTitleChunker:
    """Section-aware document chunker that preserves title boundaries.

    Implements Unstructured.io's by_title strategy:
    - Title elements start new sections
    - Chunks never span across title boundaries
    - Small sections can be combined using combine_text_under_n_chars
    - Page boundaries can be optionally respected
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        model_name: str = "cl100k_base",
        preserve_tables: bool = True,
        combine_text_under_n_chars: int | None = None,
        respect_page_boundaries: bool = False,
    ) -> None:
        """Initialize by_title chunker.

        Args:
            chunk_size: Maximum tokens per chunk (soft limit)
            chunk_overlap: Number of overlapping tokens between chunks within same section
            model_name: Tiktoken encoding model name
            preserve_tables: Whether to keep tables intact
            combine_text_under_n_chars: Combine sections smaller than this character count
            respect_page_boundaries: If True, never chunk across page boundaries
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.preserve_tables = preserve_tables
        self.combine_text_under_n_chars = combine_text_under_n_chars
        self.respect_page_boundaries = respect_page_boundaries

        try:
            self.encoding = tiktoken.get_encoding(model_name)
        except Exception as e:
            logger.warning(f"Failed to load tiktoken encoding {model_name}: {e}. Using cl100k_base.")
            self.encoding = tiktoken.get_encoding("cl100k_base")

    def chunk_document(self, document: Document) -> list[Chunk]:
        """Chunking stage: section-aware (by_title) chunking.

        **Strategy:** Semantic / section-aware. Title and heading
        elements act as section boundaries; chunks never span them
        **unless** ``combine_text_under_n_chars`` is set, in which
        case consecutive small sections are merged *before* chunking
        and the resulting combined chunk may contain more than one
        title/heading boundary by design. Within each (possibly
        merged) section, elements are packed into chunks up to
        ``chunk_size`` tokens; oversized elements form standalone
        chunks tagged ``oversized_element: True``.

        **Parameters controlling chunk size:**

        * ``chunk_size`` (default 1000): soft maximum tokens per chunk.
        * ``chunk_overlap`` (default 200): retained for API symmetry
          but **not applied** in by-title mode -- crossing a section
          boundary would defeat the strategy's purpose. Overlap inside
          a single section is also disabled by design.
        * ``preserve_tables`` (default True): tables become standalone
          chunks.
        * ``combine_text_under_n_chars`` (default None): when set, runs
          of sections whose combined text length is below this
          threshold are merged before chunking, preventing tiny
          fragments.
        * ``respect_page_boundaries`` (default False): when True,
          forces a chunk seal on page changes within a section.

        **How overlap is calculated:** Overlap is *intentionally zero*
        across both section and page boundaries; section identity is
        the more important signal for retrieval than token-window
        continuity.

        **Output schema:** A list of :class:`Chunk` with the same
        fields documented in
        :meth:`TokenChunker.chunk_document` plus:

        * ``metadata["chunking_strategy"] = "by_title"``.
        * ``metadata["section_title"]``: the first title/heading
          content found in the chunk, or None.
        * ``metadata["orig_elements"]``: list of source element IDs.

        **Side effects:** None. Pure transformation.

        Args:
            document: Parsed document with populated ``elements``.

        Returns:
            List of :class:`Chunk`. Each chunk respects section
            boundaries except where ``combine_text_under_n_chars``
            triggered an explicit small-section merge.
        """
        if not document.elements:
            logger.warning(f"Document {document.document_id} has no elements to chunk")
            return []

        chunks: list[Chunk] = []

        # Group elements by section (title boundaries)
        sections = self._group_by_sections(document.elements)

        # Optionally combine small sections
        if self.combine_text_under_n_chars:
            sections = self._combine_small_sections(sections)

        # Chunk each section independently
        for section_elements in sections:
            # Handle tables separately if configured
            if self.preserve_tables:
                tables = [e for e in section_elements if e.element_type == ElementType.TABLE]
                non_tables = [e for e in section_elements if e.element_type != ElementType.TABLE]

                # Chunk non-table elements
                if non_tables:
                    section_chunks = self._chunk_section(non_tables, document)
                    chunks.extend(section_chunks)

                # Add tables as standalone chunks
                for table in tables:
                    chunk = self._create_table_chunk(table, document)
                    chunks.append(chunk)
            else:
                # Chunk all elements in section together
                section_chunks = self._chunk_section(section_elements, document)
                chunks.extend(section_chunks)

        # Add metadata to all chunks
        for i, chunk in enumerate(chunks):
            chunk.metadata.update(
                {
                    "document_id": document.document_id,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "source_path": document.source_path,
                    "document_format": document.format.value,
                    "chunking_strategy": "by_title",
                },
            )

            # Track original elements in chunk metadata
            if chunk.elements:
                chunk.metadata["orig_elements"] = [e.metadata.element_id for e in chunk.elements]

        return chunks

    def _group_by_sections(self, elements: list[DocumentElement]) -> list[list[DocumentElement]]:
        """Group elements by section boundaries (title elements).

        Args:
            elements: All document elements

        Returns:
            List of sections, where each section is a list of elements
        """
        sections: list[list[DocumentElement]] = []
        current_section: list[DocumentElement] = []

        title_types = {
            ElementType.TITLE,
            ElementType.HEADING,
        }

        for element in elements:
            # Title element starts a new section
            if element.element_type in title_types:
                # Close previous section if it has content
                if current_section:
                    sections.append(current_section)

                # Start new section with the title
                current_section = [element]
            else:
                # Add to current section
                current_section.append(element)

        # Add final section
        if current_section:
            sections.append(current_section)

        return sections

    def _combine_small_sections(
        self,
        sections: list[list[DocumentElement]],
    ) -> list[list[DocumentElement]]:
        """Combine sections smaller than combine_text_under_n_chars.

        Args:
            sections: List of sections to potentially combine

        Returns:
            List of sections with small ones combined
        """
        if not self.combine_text_under_n_chars:
            return sections

        combined: list[list[DocumentElement]] = []
        pending: list[DocumentElement] = []

        for section in sections:
            section_text = "\n\n".join(e.content for e in section)

            if len(section_text) < self.combine_text_under_n_chars:
                # Small section - add to pending
                pending.extend(section)
            else:
                # Large section
                if pending:
                    # Flush pending small sections
                    combined.append(pending)
                    pending = []

                # Add current section
                combined.append(section)

        # Flush any remaining pending sections
        if pending:
            combined.append(pending)

        return combined

    def _chunk_section(
        self,
        section_elements: list[DocumentElement],
        document: Document,
    ) -> list[Chunk]:
        """Chunk elements within a single section.

        Args:
            section_elements: Elements in this section
            document: Source document

        Returns:
            List of chunks for this section
        """
        chunks: list[Chunk] = []
        current_content: list[str] = []
        current_elements: list[DocumentElement] = []
        current_tokens = 0

        for element in section_elements:
            element_text = element.content
            element_tokens = len(self.encoding.encode(element_text))

            # Check page boundary if configured
            if self.respect_page_boundaries and current_elements:
                current_page = element.metadata.page_number
                previous_page = current_elements[-1].metadata.page_number

                if current_page and previous_page and current_page != previous_page:
                    # Page boundary - close current chunk
                    if current_content:
                        chunk = self._create_chunk(current_content, current_elements, document)
                        chunks.append(chunk)
                        current_content = []
                        current_elements = []
                        current_tokens = 0

            # Check if element exceeds chunk size
            if element_tokens > self.chunk_size:
                # Flush current chunk first
                if current_content:
                    chunk = self._create_chunk(current_content, current_elements, document)
                    chunks.append(chunk)
                    current_content = []
                    current_elements = []
                    current_tokens = 0

                # Add large element as standalone chunk
                chunk = self._create_chunk([element_text], [element], document)
                chunk.metadata["oversized_element"] = True
                chunks.append(chunk)
                continue

            # Check if adding element would exceed chunk size
            if current_tokens + element_tokens > self.chunk_size and current_content:
                # Close current chunk
                chunk = self._create_chunk(current_content, current_elements, document)
                chunks.append(chunk)

                # Start new chunk (overlap not applied across section chunks)
                current_content = []
                current_elements = []
                current_tokens = 0

            # Add element to current chunk
            current_content.append(element_text)
            current_elements.append(element)
            current_tokens += element_tokens

        # Create final chunk if content remains
        if current_content:
            chunk = self._create_chunk(current_content, current_elements, document)
            chunks.append(chunk)

        return chunks

    def _create_chunk(
        self,
        content_parts: list[str],
        elements: list[DocumentElement],
        document: Document,
    ) -> Chunk:
        """Create a chunk from content parts and elements.

        Args:
            content_parts: List of text content
            elements: List of document elements
            document: Source document

        Returns:
            Chunk instance
        """
        content = "\n\n".join(content_parts)
        token_count = len(self.encoding.encode(content))

        # Determine page range
        page_numbers = [e.metadata.page_number for e in elements if e.metadata.page_number is not None]
        start_page = min(page_numbers) if page_numbers else None
        end_page = max(page_numbers) if page_numbers else None

        # Determine section title
        section_title = None
        for element in elements:
            if element.element_type in (ElementType.TITLE, ElementType.HEADING):
                section_title = element.content
                break

        return Chunk(
            content=content,
            elements=elements,
            token_count=token_count,
            start_page=start_page,
            end_page=end_page,
            metadata={
                "document_id": document.document_id,
                "section_title": section_title,
            },
        )

    def _create_table_chunk(self, table: DocumentElement, document: Document) -> Chunk:
        """Create a standalone chunk for a table element.

        Args:
            table: Table element
            document: Source document

        Returns:
            Chunk instance
        """
        content = table.content
        token_count = len(self.encoding.encode(content))

        return Chunk(
            content=content,
            elements=[table],
            token_count=token_count,
            start_page=table.metadata.page_number,
            end_page=table.metadata.page_number,
            metadata={
                "document_id": document.document_id,
                "type": "table",
                "page_number": table.metadata.page_number,
            },
        )
