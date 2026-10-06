"""Map a Docling JSON document into this repo's Document and element models."""

from pathlib import Path
from typing import Any

from docling_core.types.doc import (
    CodeItem,
    CoordOrigin,
    DocItem,
    DoclingDocument,
    FormulaItem,
    ListItem,
    ProvenanceItem,
    SectionHeaderItem,
    TableItem,
    TextItem,
    TitleItem,
)

from data_ingestor.core.exceptions import ConversionError
from data_ingestor.core.metadata_keys import DOCLING_JSON_KEY
from data_ingestor.core.models import (
    Document,
    DocumentElement,
    DocumentFormat,
    ElementMetadata,
    ElementType,
    ProcessingStatus,
)

__all__ = ["DOCLING_JSON_KEY", "docling_json_to_document"]

# Metadata key recording the conversion service status (for example "partial_success").
CONVERSION_STATUS_KEY = "conversion_status"

# Order matters: titles, headers, list items, code and formulas are all TextItem subclasses.
_TEXT_ELEMENT_TYPES: tuple[tuple[type[TextItem], ElementType], ...] = (
    (TitleItem, ElementType.TITLE),
    (SectionHeaderItem, ElementType.TITLE),
    (ListItem, ElementType.LIST_ITEM),
    (CodeItem, ElementType.CODE_SNIPPET),
    (FormulaItem, ElementType.FORMULA),
    (TextItem, ElementType.NARRATIVE_TEXT),
)

_FORMAT_BY_SUFFIX = {
    ".pdf": DocumentFormat.PDF,
    ".docx": DocumentFormat.DOCX,
    ".html": DocumentFormat.HTML,
    ".htm": DocumentFormat.HTML,
}

_SectionStack = list[tuple[int, str]]  # (heading level, text); a document title is level 0


def docling_json_to_document(
    docling_json: dict[str, Any],
    document_id: str,
    filename: str | None = None,
    extra_metadata: dict[str, Any] | None = None,
    document_format: DocumentFormat | None = None,
    conversion_status: str = "success",
) -> Document:
    """Build a Document whose elements keep page numbers, headings and tables.

    Args:
        docling_json: DoclingDocument JSON as returned by the conversion service
        document_id: Identifier to assign to the resulting Document
        filename: Optional original file name for element metadata; its suffix selects
            the document format when ``document_format`` is not given
        extra_metadata: Extra document-level metadata (entity, category, and so on).
            The ``docling_json`` and ``conversion_status`` keys are reserved and are
            overwritten by this function.
        document_format: Source format; derived from the filename suffix, else UNKNOWN
        conversion_status: Status reported by the conversion service. Anything other than
            ``"success"`` (for example ``"partial_success"``) marks the Document
            ``REQUIRES_REVIEW`` instead of ``COMPLETED``, because content may be missing.

    Raises:
        ConversionError: If the JSON is not a valid Docling document
    """
    try:
        doc = DoclingDocument.model_validate(docling_json)
    except ValueError as exc:
        msg = "Conversion output is not a valid Docling document"
        raise ConversionError(msg) from exc

    elements: list[DocumentElement] = []
    section_stack: _SectionStack = []

    for item, tree_depth in doc.iterate_items():
        element = _item_to_element(item, tree_depth, doc, filename, section_stack)
        if element is not None:
            elements.append(element)

    document_metadata = dict(extra_metadata or {})
    document_metadata[DOCLING_JSON_KEY] = docling_json
    document_metadata[CONVERSION_STATUS_KEY] = conversion_status
    return Document(
        document_id=document_id,
        format=document_format or _format_from_filename(filename),
        status=ProcessingStatus.COMPLETED if conversion_status == "success" else ProcessingStatus.REQUIRES_REVIEW,
        metadata=document_metadata,
        elements=elements,
        parser_used="docling-serve",
    )


def _format_from_filename(filename: str | None) -> DocumentFormat:
    if not filename:
        return DocumentFormat.UNKNOWN
    return _FORMAT_BY_SUFFIX.get(Path(filename).suffix.lower(), DocumentFormat.UNKNOWN)


def _classify(item: Any, doc: DoclingDocument) -> tuple[ElementType, str] | None:
    """Return the element type and text for an item, or None for items without indexable text.

    Pictures and other non-text items are skipped on purpose.
    """
    if isinstance(item, TableItem):
        return ElementType.TABLE, item.export_to_markdown(doc=doc)
    for item_class, element_type in _TEXT_ELEMENT_TYPES:
        if isinstance(item, item_class):
            return element_type, item.text
    return None


def _heading_level(item: Any) -> int | None:
    """Heading level of a title (0) or section header (its own level); None for other items."""
    if isinstance(item, SectionHeaderItem):
        return item.level
    if isinstance(item, TitleItem):
        return 0
    return None


def _track_section(section_stack: _SectionStack, heading_level: int, text: str) -> None:
    while section_stack and section_stack[-1][0] >= heading_level:
        section_stack.pop()
    section_stack.append((heading_level, text))


def _coordinates(prov: ProvenanceItem, doc: DoclingDocument) -> tuple[float, float, float, float]:
    """Bounding box as (left, top, right, bottom) with a top-left origin when the page is known."""
    bbox = prov.bbox
    page = doc.pages.get(prov.page_no)
    if page is not None and bbox.coord_origin != CoordOrigin.TOPLEFT:
        bbox = bbox.to_top_left_origin(page_height=page.size.height)
    return (bbox.l, bbox.t, bbox.r, bbox.b)


def _item_to_element(
    item: Any,
    tree_depth: int,
    doc: DoclingDocument,
    filename: str | None,
    section_stack: _SectionStack,
) -> DocumentElement | None:
    classified = _classify(item, doc)
    if classified is None:
        return None
    element_type, content = classified

    heading_level = _heading_level(item)
    if heading_level is not None:
        _track_section(section_stack, heading_level, item.text)

    if not content or not content.strip():
        return None

    prov = item.prov[0] if isinstance(item, DocItem) and item.prov else None
    metadata = ElementMetadata(
        filename=filename,
        page_number=prov.page_no if prov else None,
        coordinates=_coordinates(prov, doc) if prov else None,
        # Headings carry their heading level; other items carry their depth in the tree
        category_depth=heading_level if heading_level is not None else tree_depth,
        text_as_html=item.export_to_html(doc=doc) if isinstance(item, TableItem) else None,
        extra={"section_title": section_stack[-1][1] if section_stack else None},
    )
    return DocumentElement(element_type=element_type, content=content, metadata=metadata)
