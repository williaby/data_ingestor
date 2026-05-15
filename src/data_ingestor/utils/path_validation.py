"""Path validation helpers for output sinks.

These helpers exist so that any future HTTP/API surface that accepts an
output path from a remote caller can confine writes to an explicit base
directory. The current CLI does NOT call into these (a local user typing
``--output ../foo.json`` is making an authorized local choice), but any
network-exposed endpoint that takes a destination path MUST route through
``validate_output_path`` to defeat path traversal.
"""

from __future__ import annotations

from pathlib import Path


class UnsafePathError(ValueError):
    """Raised when a candidate output path escapes the allowed base directory."""


def validate_output_path(
    candidate: str | Path,
    base_dir: str | Path,
) -> Path:
    """Resolve ``candidate`` and confirm it stays inside ``base_dir``.

    Both paths are fully resolved (symlinks followed), then compared. This
    rejects both literal ``..`` traversal and symlink-based escapes from
    inside ``base_dir``.

    Args:
        candidate: Caller-supplied destination path. May be relative; if so,
            it's resolved against ``base_dir``.
        base_dir: The directory that callers are allowed to write into.

    Returns:
        The fully resolved, safe ``Path`` to write to.

    Raises:
        UnsafePathError: If the resolved candidate is not inside ``base_dir``.
    """
    base_resolved = Path(base_dir).resolve()
    candidate_path = Path(candidate)
    if not candidate_path.is_absolute():
        candidate_path = base_resolved / candidate_path
    # strict=False so the file itself need not exist yet (we're about to
    # create it), but its resolved parents must.
    resolved = candidate_path.resolve(strict=False)
    try:
        resolved.relative_to(base_resolved)
    except ValueError as exc:
        msg = f"Output path {resolved} is outside allowed base {base_resolved}"
        raise UnsafePathError(msg) from exc
    return resolved
