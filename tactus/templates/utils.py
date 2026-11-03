"""Utilities for resolving local and default tactus templates."""
from contextlib import contextmanager
from importlib import resources
from pathlib import Path
from collections.abc import Iterator


@contextmanager
def resolve_template(
    relative_path: str | Path,
    *,
    local_root: str | Path | None = None,
    package: str = "tactus",
) -> Iterator[Path]:
    """Resolve a template, preferring a local override over the package default."""

    relative_path = Path(relative_path)

    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError("Template path must be relative and cannot contain '..'.")

    # 1. Check the local project directory.
    local_root = Path.cwd() if local_root is None else Path(local_root)
    local_path = (local_root / relative_path).resolve()

    if local_path.is_file():
        yield local_path
        return

    # 2. Fall back to the template shipped with package.
    resource = resources.files(package).joinpath(*relative_path.parts)

    if not resource.is_file():
        raise FileNotFoundError(
            f"Template '{relative_path}' not found locally or in package '{package}'."
        )

    with resources.as_file(resource) as default_path:
        yield default_path