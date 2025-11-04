"""Token-based chunking strategies for document segmentation."""

import logging

import tiktoken

from data_ingestor.core.models import Chunk, Document, DocumentElement, ElementType

logger = logging.getLogger(__name__)


class TokenChunker:
    """Token-based document chunker with overlap support."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        model_name: str = "cl100k_base",
        preserve_tables: bool = True,
    ) -> None:
        """Initialize token chunker.

        # #CRITICAL: Token Counting: Encoding model must match target LLM
        # #VERIFY: Allow configuration of encoding model for different LLMs

        Args:
            chunk_size: Maximum tokens per chunk
            chunk_overlap: Number of overlapping tokens between chunks
            model_name: Tiktoken encoding model name
            preserve_tables: Whether to keep tables intact
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.preserve_tables = preserve_tables

        try:
            self.encoding = tiktoken.get_encoding(model_name)
        except Exception as e:
            logger.warning(f"Failed to load tiktoken encoding {model_name}: {e}. Using cl100k_base.")
            self.encoding = tiktoken.get_encoding("cl100k_base")

    def chunk_document(self, document: Document) -> list[Chunk]:
        """Chunk document into smaller pieces with overlap.

        # #CRITICAL: Context Preservation: Chunking may split semantic units
        # #VERIFY: Implement semantic boundary detection for better splits

        Args:
            document: Document with extracted elements

        Returns:
            List of chunks
        """
        if not document.elements:
            logger.warning(f"Document {document.document_id} has no elements to chunk")
            return []

        chunks: list[Chunk] = []

        # Handle tables separately if configured
        if self.preserve_tables:
            table_elements = [e for e in document.elements if e.element_type == ElementType.TABLE]
            non_table_elements = [e for e in document.elements if e.element_type != ElementType.TABLE]

            # Chunk non-table elements
            chunks.extend(self._chunk_elements(non_table_elements, document))

            # Add tables as single chunks
            for table_element in table_elements:
                chunk = Chunk(
                    content=table_element.content,
                    elements=[table_element],
                    metadata={
                        "document_id": document.document_id,
                        "type": "table",
                        "page_number": table_element.page_number,
                    },
                )
                chunk.token_count = len(self.encoding.encode(chunk.content))
                chunks.append(chunk)

        else:
            # Chunk all elements together
            chunks.extend(self._chunk_elements(document.elements, document))

        # Add document-level metadata to all chunks
        for i, chunk in enumerate(chunks):
            chunk.metadata.update(
                {
                    "document_id": document.document_id,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "source_path": document.source_path,
                    "document_format": document.format.value,
                },
            )

        return chunks

    def _chunk_elements(self, elements: list[DocumentElement], document: Document) -> list[Chunk]:
        """Chunk a list of elements with token-based splitting.

        Args:
            elements: Elements to chunk
            document: Source document

        Returns:
            List of chunks
        """
        chunks: list[Chunk] = []
        current_content: list[str] = []
        current_elements: list[DocumentElement] = []
        current_tokens = 0

        for element in elements:
            element_text = element.content
            element_tokens = len(self.encoding.encode(element_text))

            # If single element exceeds chunk size, split it
            # #EDGE: Large Elements: Single element may exceed chunk size
            # #VERIFY: Split large elements at sentence boundaries
            if element_tokens > self.chunk_size:
                # Flush current chunk first
                if current_content:
                    chunk = self._create_chunk(current_content, current_elements, document)
                    chunks.append(chunk)
                    current_content = []
                    current_elements = []
                    current_tokens = 0

                # Split large element
                split_chunks = self._split_large_element(element, document)
                chunks.extend(split_chunks)
                continue

            # Check if adding this element would exceed chunk size
            if current_tokens + element_tokens > self.chunk_size and current_content:
                # Create chunk from accumulated content
                chunk = self._create_chunk(current_content, current_elements, document)
                chunks.append(chunk)

                # Start new chunk with overlap
                if self.chunk_overlap > 0 and current_content:
                    overlap_content, overlap_tokens = self._get_overlap(current_content)
                    current_content = overlap_content
                    current_elements = []  # Don't track elements in overlap
                    current_tokens = overlap_tokens
                else:
                    current_content = []
                    current_elements = []
                    current_tokens = 0

            # Add element to current chunk
            current_content.append(element_text)
            current_elements.append(element)
            current_tokens += element_tokens

        # Create final chunk if there's remaining content
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
        page_numbers = [e.page_number for e in elements if e.page_number is not None]
        start_page = min(page_numbers) if page_numbers else None
        end_page = max(page_numbers) if page_numbers else None

        return Chunk(
            content=content,
            elements=elements,
            token_count=token_count,
            start_page=start_page,
            end_page=end_page,
            metadata={"document_id": document.document_id},
        )

    def _get_overlap(self, content_parts: list[str]) -> tuple[list[str], int]:
        """Get overlap content from end of current chunk.

        Args:
            content_parts: Current content parts

        Returns:
            Tuple of (overlap content parts, token count)
        """
        overlap_parts: list[str] = []
        overlap_tokens = 0

        # Work backwards through content until we reach overlap size
        for content in reversed(content_parts):
            tokens = len(self.encoding.encode(content))
            if overlap_tokens + tokens <= self.chunk_overlap:
                overlap_parts.insert(0, content)
                overlap_tokens += tokens
            else:
                break

        return overlap_parts, overlap_tokens

    def _split_large_element(self, element: DocumentElement, document: Document) -> list[Chunk]:
        """Split a large element that exceeds chunk size.

        # #EDGE: Large Elements: Must split at reasonable boundaries
        # #VERIFY: Use sentence tokenization for better splits

        Args:
            element: Element to split
            document: Source document

        Returns:
            List of chunks
        """
        chunks: list[Chunk] = []
        text = element.content

        # Simple sentence-based splitting
        # #ASSUME: Text Processing: Simple period split may break mid-sentence
        # #VERIFY: Use proper sentence tokenization library
        sentences = text.split(". ")

        current_content: list[str] = []
        current_tokens = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Add period back if it was removed
            if not sentence.endswith("."):
                sentence += "."

            sentence_tokens = len(self.encoding.encode(sentence))

            if current_tokens + sentence_tokens > self.chunk_size and current_content:
                # Create chunk
                content = " ".join(current_content)
                chunk = Chunk(
                    content=content,
                    elements=[element],
                    token_count=len(self.encoding.encode(content)),
                    metadata={
                        "document_id": document.document_id,
                        "split_from_large_element": True,
                        "element_type": element.element_type.value,
                    },
                )
                chunks.append(chunk)

                # Reset with overlap
                if self.chunk_overlap > 0 and current_content:
                    # Keep last few sentences for overlap
                    overlap_text = " ".join(current_content[-3:])
                    overlap_tokens = len(self.encoding.encode(overlap_text))
                    if overlap_tokens <= self.chunk_overlap:
                        current_content = current_content[-3:]
                        current_tokens = overlap_tokens
                    else:
                        current_content = []
                        current_tokens = 0
                else:
                    current_content = []
                    current_tokens = 0

            current_content.append(sentence)
            current_tokens += sentence_tokens

        # Create final chunk if content remains
        if current_content:
            content = " ".join(current_content)
            chunk = Chunk(
                content=content,
                elements=[element],
                token_count=len(self.encoding.encode(content)),
                metadata={
                    "document_id": document.document_id,
                    "split_from_large_element": True,
                    "element_type": element.element_type.value,
                },
            )
            chunks.append(chunk)

        return chunks
