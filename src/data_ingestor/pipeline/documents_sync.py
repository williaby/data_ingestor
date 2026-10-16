"""Chunk the documents a document store lists, and keep tax-return consent current."""

import logging
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from data_ingestor.core.config import Settings
from data_ingestor.core.exceptions import DataIngestorError
from data_ingestor.export import ConsentAction, reconcile_consent, write_chunk_set
from data_ingestor.pipeline.chunk_job import build_document_chunk_set
from data_ingestor.sources import TAX_RETURNS_CATEGORY, DocumentRecord, DocumentsApiClient

logger = logging.getLogger(__name__)


@dataclass
class SyncReport:
    """What one run did, by document ID only (titles and text can be personal)."""

    chunked: list[str] = field(default_factory=list)
    withdrawn: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)
    newest_updated_at: datetime | None = None

    @property
    def ok(self) -> bool:
        """True when no document failed."""
        return not self.failed


def sync_documents(
    client: DocumentsApiClient,
    settings: Settings,
    output_dir: Path,
    *,
    updated_since: datetime | None = None,
) -> SyncReport:
    """Chunk every document updated since a time, and check consent on every tax return.

    Two listings are read: documents updated since ``updated_since`` (all documents when it is
    None), and every document in the Tax Returns category regardless of ``updated_since``.
    Each tax return is reconciled against its stored chunk set on every run, because consent can
    be withdrawn without the document changing: a withdrawn document's chunk set is rewritten
    without text. A document in the updated listing is converted and chunked again; a consented
    tax return that was not updated is left as it is.

    Consent is checked again against the document's current record just before conversion and
    just before the chunk set is written, so consent withdrawn in between never reaches disk.

    # #CRITICAL: Security: no chunk text of a tax return is written without consent on file now
    # #VERIFY: tests/unit/test_chunk_from_llc_manager.py (consent withdrawn between and during steps)
    # #EDGE: A tax return deleted in the document store leaves the listing, so its stored chunk set
    # is not withdrawn by this run
    # #VERIFY: remove a deleted document's chunk set through the retention process

    Args:
        client: Document store client
        settings: Application settings
        output_dir: Chunk-set directory
        updated_since: Only chunk documents updated at or after this time

    Returns:
        The report; ``failed`` lists documents that must be retried, so the caller should not
        move its ``updated_since`` mark past them

    Raises:
        DocumentSourceError: If a listing cannot be read at all
    """
    updated = client.list_documents(updated_since=updated_since)
    tax_returns = client.list_documents(category=TAX_RETURNS_CATEGORY)

    report = SyncReport(newest_updated_at=max((r.updated_at for r in updated), default=None))
    updated_ids = {record.id for record in updated}
    candidates = {record.id: record for record in [*tax_returns, *updated]}
    for record in sorted(candidates.values(), key=lambda r: (r.updated_at, str(r.id))):
        document_id = str(record.id)
        try:
            _sync_one(client, settings, output_dir, record, in_updated=record.id in updated_ids, report=report)
        except OSError as exc:
            logger.warning("Failed %s: %s", document_id, type(exc).__name__)
            report.failed.append((document_id, f"file operation failed: {exc}"))
        except (DataIngestorError, ValueError) as exc:
            logger.warning("Failed %s: %s", document_id, type(exc).__name__)
            report.failed.append((document_id, str(exc)))
    return report


def _record_action(action: ConsentAction, document_id: str, report: SyncReport) -> bool:
    """Note a terminal consent outcome; return True when the document needs no chunking."""
    if action is ConsentAction.WITHDRAWN:
        report.withdrawn.append(document_id)
        return True
    if action is ConsentAction.SKIP:
        report.skipped.append(document_id)
        return True
    return False


def _sync_one(
    client: DocumentsApiClient,
    settings: Settings,
    output_dir: Path,
    listed: DocumentRecord,
    *,
    in_updated: bool,
    report: SyncReport,
) -> None:
    document_id = str(listed.id)
    action = _reconcile(listed, output_dir, document_id)
    if _record_action(action, document_id, report):
        return
    if not in_updated and action is not ConsentAction.CHUNK:
        report.unchanged.append(document_id)
        return

    # The listing can be out of date by the time the document is reached, so use its current record.
    current = client.get_document(listed.id)
    if current is None:
        report.skipped.append(document_id)
        return
    if _record_action(_reconcile(current, output_dir, document_id), document_id, report):
        return

    with tempfile.TemporaryDirectory(prefix="chunk-") as scratch:
        downloaded = client.download_file(listed.id, Path(scratch))
        if current.sha256 is not None and current.sha256 != downloaded.sha256:
            msg = "the file changed after its record was read; it will be retried next run"
            raise DataIngestorError(msg)
        fields = current.document_fields(downloaded.sha256)
        chunk_set = build_document_chunk_set(
            settings,
            downloaded.path,
            document_id=document_id,
            document_fields=fields,
        )

    # #CRITICAL: Security: consent can be withdrawn while the file converts, so check it again
    # #VERIFY: tests/unit/test_chunk_from_llc_manager.py::test_consent_withdrawn_while_the_document_is_converting_is_not_written
    latest = client.get_document(listed.id)
    if latest is None:
        report.skipped.append(document_id)
        return
    if _record_action(_reconcile(latest, output_dir, document_id), document_id, report):
        return
    if latest.updated_at != current.updated_at or latest.document_fields(downloaded.sha256) != fields:
        msg = "the record changed while the file was converted; it will be retried next run"
        raise DataIngestorError(msg)
    write_chunk_set(chunk_set, output_dir, file_mode=int(settings.chunks_file_mode, 8))
    report.chunked.append(document_id)


def _reconcile(record: DocumentRecord, output_dir: Path, document_id: str) -> ConsentAction:
    try:
        return reconcile_consent(document_id, record.document_fields(), output_dir)
    except OSError as exc:
        # The stored set may still hold consented text, so say plainly that withdrawal failed.
        msg = f"consent withdrawal write failed ({type(exc).__name__}); the stored chunk set was not replaced"
        raise DataIngestorError(msg) from exc
