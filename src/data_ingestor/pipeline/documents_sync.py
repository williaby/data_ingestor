"""Chunk the documents a document store lists, and keep tax-return consent current."""

import logging
import tempfile
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from data_ingestor.core.config import Settings
from data_ingestor.core.exceptions import DataIngestorError, DocumentNotFoundError
from data_ingestor.export import (
    ConsentAction,
    is_tax_return,
    reconcile_consent,
    stored_tax_return_ids,
    withdraw_stored_chunk_set,
    write_chunk_set,
)
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

    A tax return that was deleted in the document store no longer appears in any listing and
    answers 404. After the listings, every stored chunk set that is a tax return by its own fields
    and was not reached above is looked up: a document that is gone has its stored set rewritten
    without text, and one that exists but sits outside the Tax Returns category is reconciled like
    any other. A 404 met while chunking a tax return is handled the same way.

    # #CRITICAL: Security: no chunk text of a tax return is written without consent on file now,
    # and none stays on disk once the document is deleted
    # #VERIFY: tests/unit/test_chunk_from_llc_manager.py (consent withdrawn or document deleted
    # between and during steps; deleted tax returns)
    # #ASSUME: the document store answers 404 only for a document that is gone; a deleted
    # document is not told apart from one that never existed
    # #VERIFY: confirm the soft-delete behaviour of GET /api/v1/documents/{id} with the document
    # store owner

    Args:
        client: Document store client
        settings: Application settings
        output_dir: Chunk-set directory
        updated_since: Only chunk documents updated at or after this time

    Returns:
        The report; ``failed`` lists documents that must be retried, so the caller should not
        move its ``updated_since`` mark past them

    Raises:
        DocumentSourceError: If a listing cannot be read completely
    """
    updated = client.list_documents(updated_since=updated_since)
    tax_returns = client.list_documents(category=TAX_RETURNS_CATEGORY)

    report = SyncReport(newest_updated_at=max((r.updated_at for r in updated), default=None))
    sync = _Sync(client, settings, output_dir, report)
    updated_ids = {record.id for record in updated}
    candidates = {record.id: record for record in [*tax_returns, *updated]}
    for record in sorted(candidates.values(), key=lambda r: (r.updated_at, str(r.id))):
        sync.guarded(str(record.id), sync.sync_record, record, record.id in updated_ids)
    for document_id in stored_tax_return_ids(output_dir):
        if uuid.UUID(document_id) not in candidates:
            sync.guarded(document_id, sync.sync_stored, document_id)
    return report


class _Sync:
    """One run's collaborators and the per-document steps."""

    def __init__(self, client: DocumentsApiClient, settings: Settings, output_dir: Path, report: SyncReport) -> None:
        self._client = client
        self._settings = settings
        self._output_dir = output_dir
        self._report = report
        self._file_mode = int(settings.chunks_file_mode, 8)

    def guarded(self, document_id: str, step: Callable[..., None], *args: object) -> None:
        """Run one document's step; a failure is recorded and does not stop the run."""
        try:
            step(*args)
        except OSError as exc:
            logger.warning("Failed %s: %s", document_id, type(exc).__name__)
            self._report.failed.append((document_id, f"file operation failed: {exc}"))
        except (DataIngestorError, ValueError) as exc:
            logger.warning("Failed %s: %s", document_id, type(exc).__name__)
            self._report.failed.append((document_id, str(exc)))

    # -- consent ---------------------------------------------------------------------

    def _reconcile(self, record: DocumentRecord) -> ConsentAction:
        try:
            return reconcile_consent(
                str(record.id),
                record.document_fields(),
                self._output_dir,
                file_mode=self._file_mode,
            )
        except OSError as exc:
            raise _withdrawal_failed(exc) from exc

    def _settled(self, action: ConsentAction, document_id: str) -> bool:
        """Note a terminal consent outcome; True when the document needs no chunking."""
        if action is ConsentAction.WITHDRAWN:
            self._report.withdrawn.append(document_id)
            return True
        if action is ConsentAction.SKIP:
            self._report.skipped.append(document_id)
            return True
        return False

    def _withdraw_gone(self, document_id: str) -> None:
        """Rewrite a deleted tax return's stored set without text."""
        try:
            action = withdraw_stored_chunk_set(document_id, self._output_dir, file_mode=self._file_mode)
        except OSError as exc:
            raise _withdrawal_failed(exc) from exc
        self._settled(action, document_id)

    def _vanished(self, current: DocumentRecord | None, listed: DocumentRecord) -> bool:
        """True when the document is gone; a tax return's stored text is withdrawn."""
        if current is not None:
            return False
        document_id = str(listed.id)
        if is_tax_return(listed.document_fields()):
            self._withdraw_gone(document_id)
        else:
            self._report.skipped.append(document_id)
        return True

    # -- documents -------------------------------------------------------------------

    def sync_stored(self, document_id: str) -> None:
        """Check a stored tax return the listings did not reach (deleted, or in another category)."""
        record = self._client.get_document(document_id)
        if record is None:
            self._withdraw_gone(document_id)
        else:
            self.sync_record(record, in_updated=False)

    def sync_record(self, listed: DocumentRecord, in_updated: bool) -> None:
        """Reconcile consent for one listed document, then chunk it when it needs chunking."""
        document_id = str(listed.id)
        action = self._reconcile(listed)
        if self._settled(action, document_id):
            return
        if not in_updated and action is not ConsentAction.CHUNK:
            self._report.unchanged.append(document_id)
            return
        self._chunk(listed)

    def _chunk(self, listed: DocumentRecord) -> None:
        document_id = str(listed.id)
        # The listing can be out of date by the time the document is reached: use its current record.
        current = self._client.get_document(listed.id)
        if self._vanished(current, listed) or current is None:
            return
        if self._settled(self._reconcile(current), document_id):
            return
        converted = self._convert(current)
        if converted is None:
            self._vanished(None, listed)
            return
        chunk_set, fields = converted

        # #CRITICAL: Security: consent can be withdrawn, or the document deleted, while the file
        # converts, so the record is read again before anything is written
        # #VERIFY: tests/unit/test_chunk_from_llc_manager.py::test_consent_withdrawn_while_the_document_is_converting_is_not_written
        latest = self._client.get_document(listed.id)
        if self._vanished(latest, listed) or latest is None:
            return
        if self._settled(self._reconcile(latest), document_id):
            return
        sha256 = fields["sha256"]
        if latest.updated_at != current.updated_at or latest.document_fields(sha256) != fields:
            msg = "the record changed while the file was converted; it will be retried next run"
            raise DataIngestorError(msg)
        write_chunk_set(chunk_set, self._output_dir, file_mode=self._file_mode)
        self._report.chunked.append(document_id)

    def _convert(self, current: DocumentRecord) -> tuple[dict[str, Any], dict[str, Any]] | None:
        """Download and chunk one document; None when its file is gone because it was deleted."""
        with tempfile.TemporaryDirectory(prefix="chunk-") as scratch:
            try:
                downloaded = self._client.download_file(current.id, Path(scratch))
            except DocumentNotFoundError:
                if self._client.get_document(current.id) is None:
                    return None
                raise
            if current.sha256 is not None and current.sha256 != downloaded.sha256:
                msg = "the file changed after its record was read; it will be retried next run"
                raise DataIngestorError(msg)
            fields = current.document_fields(downloaded.sha256)
            chunk_set = build_document_chunk_set(
                self._settings,
                downloaded.path,
                document_id=str(current.id),
                document_fields=fields,
            )
        return chunk_set, fields


def _withdrawal_failed(exc: OSError) -> DataIngestorError:
    # The stored set may still hold consented text, so say plainly that withdrawal failed.
    msg = f"consent withdrawal write failed ({type(exc).__name__}); the stored chunk set was not replaced"
    return DataIngestorError(msg)
