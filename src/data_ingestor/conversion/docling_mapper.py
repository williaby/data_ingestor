"""Map a Docling JSON document into this repo's Document and element models."""

from typing import Any

from docling_core.types.doc import (
    CodeItem,
    DoclingDocument,
    FormulaItem,
    ListItem,
    SectionHeaderItem,
    TableItem,
    TextItem,
    TitleItem,
)

from data_ingestor.core.exceptions import ConversionError
from data_ingestor.core.models import (
    Document,
    DocumentElement,
    DocumentFormat,
    ElementMetadata,
    ElementType,
    ProcessingStatus,
)

# Key under which the original Docling tree travels with the Document.
# Structure-aware chunkers (HybridChunker) need the tree, not just the flat elements.
DOCLING_JSON_KEY = "docling_json"


def docling_json_to_document(
    docling_json: dict[str, Any],
    document_id: str,
    filename: str | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> Document:
    """Build a Document whose elements keep page numbers, headings and tables.

    Args:
        docling_json: DoclingDocument JSON as returned by the conversion service
        document_id: Identifier to assign to the resulting Document
        filename: Optional original file name for element metadata
        extra_metadata: Extra document-level metadata (entity, category, and so on)

    Raises:
        ConversionError: If the JSON is not a valid Docling document
    """
    try:
        doc = DoclingDocument.model_validate(docling_json)
    except ValueError as exc:
        msg = "Conversion output is not a valid Docling document"
        raise ConversionError(msg) from exc

    elements: list[DocumentElement] = []
    section_stack: list[tuple[int, str]] = []  # (heading level, text); a document title is level 0

    for item, level in doc.iterate_items():
        if isinstance(item, (SectionHeaderItem, TitleItem)):
            heading_level = item.level if isinstance(item, SectionHeaderItem) else 0
            while section_stack and section_stack[-1][0] >= heading_level:
                section_stack.pop()
            section_stack.append((heading_level, item.text))
            element_type = ElementType.TITLE
            content = item.text
        elif isinstance(item, ListItem):
            element_type, content = ElementType.LIST_ITEM, item.text
        elif isinstance(item, CodeItem):
            element_type, content = ElementType.CODE_SNIPPET, item.text
        elif isinstance(item, TableItem):
            element_type, content = ElementType.TABLE, item.export_to_markdown(doc=doc)
        elif isinstance(item, FormulaItem):
            element_type, content = ElementType.FORMULA, item.text
        elif isinstance(item, TextItem):
            element_type, content = ElementType.NARRATIVE_TEXT, item.text
        else:
            continue  # pictures and other non-text items carry no indexable text

        if not content or not content.strip():
            continue

        prov = item.prov[0] if getattr(item, "prov", None) else None
        metadata = ElementMetadata(
            filename=filename,
            page_number=prov.page_no if prov else None,
            coordinates=(prov.bbox.l, prov.bbox.t, prov.bbox.r, prov.bbox.b) if prov else None,
            category_depth=level,
            text_as_html=item.export_to_html(doc=doc) if isinstance(item, TableItem) else None,
            extra={"section_title": section_stack[-1][1] if section_stack else None},
        )
        elements.append(DocumentElement(element_type=element_type, content=content, metadata=metadata))

    document_metadata = dict(extra_metadata or {})
    document_metadata[DOCLING_JSON_KEY] = docling_json
    return Document(
        document_id=document_id,
        format=DocumentFormat.PDF,
        status=ProcessingStatus.COMPLETED,
        metadata=document_metadata,
        elements=elements,
        parser_used="docling-serve",
    )
