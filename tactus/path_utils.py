"""Generic utilities for resolving paths across ordered search locations."""

import sys
from collections.abc import Iterable
from pathlib import Path

from .logs import logger


def resolve_path(
    path: str | Path,
    *,
    searchpaths: Iterable[str | Path] = (),
    ignore_errors: bool = False,
) -> Path:
    """Resolve an explicitly supplied path using one shared policy.

    Resolution is deliberately consistent for config and schema files:

    1. An existing path relative to the current working directory wins.
    2. Otherwise, relative paths are checked beneath the ordered ``searchpaths``
       and then beneath ``sys.path`` entries.
    3. For an absolute path that no longer exists, its suffix beneath any
       search root is tried beneath every root.
    4. Multiple distinct matches are rejected rather than silently selecting
       one.

    ``searchpaths`` are domain-specific roots (for example, configured schema
    directories); ``sys.path`` is always included as the common package fallback.
    """
    requested_path = Path(path).expanduser()
    absolute_path = requested_path.resolve()

    if absolute_path.exists():
        return absolute_path

    if isinstance(searchpaths, (str, Path)):
        searchpaths = [searchpaths]

    # Normalize and de-duplicate the roots while preserving their precedence.
    roots = []
    for root in searchpaths:
        root_resolved = Path(root).expanduser().resolve()
        if root_resolved not in roots:
            roots.append(root_resolved)

    for root in sys.path:
        if not root:
            continue
        root_resolved = Path(root).expanduser().resolve()
        if root_resolved not in roots:
            # Stale roots still identify a relative suffix from another install.
            roots.append(root_resolved)

    candidates = set()
    if requested_path.is_absolute():
        # For absolute paths, preserve the historical behavior: when the path
        # belonged to one import root, try the same relative suffix in all roots.
        relative_paths = set()
        for root in roots:
            if absolute_path.is_relative_to(root):
                relative_paths.add(absolute_path.relative_to(root))
        for relative_path in relative_paths:
            for root in roots:
                candidate = (root / relative_path).resolve()
                if candidate.exists():
                    candidates.add(candidate)
    else:
        # Relative paths are interpreted beneath each configured/package root,
        # after the current-working-directory check above.
        for root in roots:
            candidate = (root / requested_path).resolve()
            if candidate.exists():
                candidates.add(candidate)

    if len(candidates) > 1:
        raise ValueError(
            f"Ambiguous path resolution for {absolute_path}. "
            "Multiple candidates found across search paths:\n"
            + "\n".join(f"  {candidate}" for candidate in sorted(candidates))
        )
    if candidates:
        return next(iter(candidates))

    if not ignore_errors:
        raise FileNotFoundError(
            f"File {absolute_path} not found locally or beneath configured search paths"
        )
    return absolute_path


def resolve_from_searchpaths(
    subpath: str | Path,
    searchpaths: Iterable[str | Path],
    *,
    last: bool = False,
) -> Path:
    """Resolve a relative subpath recursively beneath ordered search directories.

    Use :func:`resolve_path` for explicit config/schema file arguments. This
    recursive lookup is intended for Tactus data assets and included sections,
    where a path may intentionally be named by a subpath or basename.
    """
    subpath = Path(subpath)
    if subpath.is_absolute():
        if subpath.exists():
            return subpath.resolve()
        raise RuntimeError(f"Could not find {subpath}")

    return_index = -1 if last else 0
    pattern = f"**/{subpath}"
    for searchpath in searchpaths:
        search_path = Path(searchpath)
        results = list(search_path.rglob(pattern))
        if len(results) > 1 and not last:
            logger.warning("Multiple matches found for subpath: {}", subpath)
            logger.warning("Selecting the first result: {}", results[0])
        if results:
            return results[return_index].resolve()

    raise RuntimeError(f"Could not find {subpath}")
