"""Utilities for resolving paths across ordered search directories."""

from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from importlib import resources
from pathlib import Path

from .logs import logger


def path_from_subpath(subpath, searchpaths, last=False) -> Path:
    """Find a path by subpath in an ordered list of search directories.

    The first search directory containing a match wins. Within that directory,
    the first match is returned unless ``last`` is true.

    Args:
        subpath (str | Path): Relative path or subpath to find.
        searchpaths (list[str | Path]): Directories to search, in priority order.
        last (bool): Return the last match within the first matching directory.

    Returns:
        Path: The resolved path.

    Raises:
        RuntimeError: If the path cannot be found.
    """
    subpath = Path(subpath)
    if subpath.is_absolute():
        if subpath.exists():
            return subpath
        raise RuntimeError(f"Could not find {subpath}")

    return_index = -1 if last else 0
    pattern = f"**/{subpath}"
    for searchpath in searchpaths:
        results = list(Path(searchpath).rglob(pattern))
        if len(results) > 1 and not last:
            logger.warning("Multiple matches found for subpath: {}", subpath)
            logger.warning("Selecting the first result: {}", results[0])

        if results:
            return results[return_index]

    raise RuntimeError(f"Could not find {subpath}")


@contextmanager
def resolve_file(
    file_path: str | Path,
    *,
    searchpaths: Iterable[str | Path] | str | Path | None = None,
    package: str | None = None,
) -> Iterator[Path]:
    """Resolve a file from search directories or an optional package resource.

    Search directories are checked in order, using the same recursive lookup
    behavior as :func:`path_from_subpath`. If no local file is found and
    ``package`` is provided, the file is looked up relative to that package.
    Package resources are exposed as paths for the duration of the context.

    Args:
        file_path (str | Path): Relative path to the file, or an absolute path.
        searchpaths (Iterable[str | Path] | str | Path | None): Directories to
            search in priority order. Defaults to the current working directory.
        package (str | None): Optional package to search after the local paths.

    Yields:
        Path: The resolved file path.

    Raises:
        ValueError: If a relative path contains ``..``.
        FileNotFoundError: If the file cannot be found.
    """
    file_path = Path(file_path)

    if file_path.is_absolute():
        if file_path.is_file():
            yield file_path.resolve()
            return
        raise FileNotFoundError(f"File '{file_path}' not found.")

    if ".." in file_path.parts:
        raise ValueError("File path cannot contain '..'.")

    if searchpaths is None:
        searchpaths = [Path.cwd()]
    elif isinstance(searchpaths, (str, Path)):
        searchpaths = [searchpaths]

    try:
        local_path = path_from_subpath(file_path, searchpaths).resolve()
    except RuntimeError:
        local_path = None

    if local_path is not None and local_path.is_file():
        yield local_path
        return

    if package is not None:
        resource = resources.files(package).joinpath(*file_path.parts)
        if resource.is_file():
            with resources.as_file(resource) as package_path:
                yield package_path
            return

    raise FileNotFoundError(f"File '{file_path}' not found.")
