"""Ingestion: find and read the corpus files to index."""

import sys
from pathlib import Path

from tqdm import tqdm

from src.config import EXCLUDED_DIRS, EXTENSIONS
from src.models import Document


def _list_files(root: Path, extensions: set[str] = EXTENSIONS,
                excluded: set[str] = EXCLUDED_DIRS) -> list[Path]:
    """List the corpus files to index, recursively and in sorted order.

    Args:
        root: Directory to walk through.
        extensions: File extensions to keep (e.g. ``".py"``).
        excluded: Directory names to skip anywhere in the path.

    Returns:
        The kept file paths, sorted so the result is the same on every run.
    """
    files = root.rglob("*")
    files_kept = []

    for p in files:
        is_excluded = any(part in excluded for part in p.parts)
        if p.is_file() and p.suffix in extensions and not is_excluded:
            files_kept.append(p)

    return sorted(files_kept)


def _read_file(path: Path) -> str | None:
    """Read a text file as UTF-8, keeping its line endings unchanged.

    ``newline=""`` keeps ``\\r\\n`` as is, so character offsets match the
    file on disk. Errors are reported on stderr instead of being raised.

    Args:
        path: File to read.

    Returns:
        The file content, or None if the file cannot be read (missing,
        a directory, no permission, or not valid UTF-8).
    """
    try:
        with open(path, encoding="utf-8", newline="") as f:
            return f.read()
    except (UnicodeDecodeError, OSError) as e:
        print(f"Warning: cannot read {path}: {e}", file=sys.stderr)
        return None


def ingest(root: Path,
           extensions: set[str] = EXTENSIONS,
           excluded: set[str] = EXCLUDED_DIRS) -> list[Document]:
    """Read every corpus file to index and wrap it in a Document.

    Files that cannot be read, and files that are empty or contain only
    whitespace, are skipped.

    Args:
        root: Directory to walk through (e.g. ``Path("data/raw")``).
        extensions: File extensions to keep (e.g. ``".py"``).
        excluded: Directory names to skip anywhere in the path.

    Returns:
        One Document per kept file, in sorted path order. Each file_path
        uses ``/`` separators (e.g. ``data/raw/vllm-0.10.1/README.md``).
    """
    listed_files = _list_files(root, extensions, excluded)
    documents: list[Document] = []
    for path in tqdm(listed_files, desc="Reading files"):
        content = _read_file(path)
        if content is None or not content.strip():
            continue
        documents.append(Document(file_path=path.as_posix(), content=content))
    return documents
