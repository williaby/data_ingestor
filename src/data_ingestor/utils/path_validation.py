"""Path validation helpers for output sinks.

These helpers exist so that any future HTTP/API surface that accepts an
output path from a remote caller can confine writes to an explicit base
directory. The current CLI does NOT call into these (a local user typing
``--output ../foo.json`` is making an authorized local choice), but any
network-exposed endpoint that takes a destination path MUST route through
``validate_output_path`` to defeat path traversal.

# #ASSUME: CLI callers are authorized local users; only network-exposed
#   callers must route through validate_output_path.
# #CRITICAL: any future API endpoint that accepts a caller-supplied
#   destination path MUST call validate_output_path before opening the file,
#   or the API gains a path-traversal sink.
# #EDGE: this is name-resolution-time validation, not open-time. An
#   attacker with write access to ``base_dir`` could swap a path component
#   for a symlink between the call to validate_output_path and the
#   subsequent ``open()``. If TOCTOU resistance is required, callers must
#   re-open under an O_NOFOLLOW / openat(base_dir_fd, ...) discipline; this
#   helper does not provide that.
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
    rejects both literal ``..`` traversal and symlink-based escapes that
    exist **at call time**. See the module docstring's ``#EDGE`` note: this
    helper does NOT defeat a TOCTOU symlink swap that happens between the
    return of this function and a later ``open()``. Callers that need that
    guarantee must open the file under an ``openat(base_dir_fd, O_NOFOLLOW)``
    discipline themselves.

    Args:
        candidate: Caller-supplied destination path. May be relative; if so,
            it's resolved against ``base_dir``.
        base_dir: The directory that callers are allowed to write into.

    Returns:
        The fully resolved ``Path``, confirmed inside ``base_dir`` at call time.

    Raises:
        UnsafePathError: If the resolved candidate is not inside ``base_dir``.
    """
    base_resolved = Path(base_dir).resolve()
    candidate_path = Path(candidate)
    if not candidate_path.is_absolute():
        candidate_path = base_resolved / candidate_path
    # strict=False so the path is normalized (".." segments collapsed,
    # existing symlink components followed) without requiring that the
    # candidate or its parents already exist — callers typically invoke
    # this just before creating the file.
    resolved = candidate_path.resolve(strict=False)
    try:
        resolved.relative_to(base_resolved)
    except ValueError as exc:
        msg = f"Output path {resolved} is outside allowed base {base_resolved}"
        raise UnsafePathError(msg) from exc
    return resolved
