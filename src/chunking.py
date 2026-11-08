"""Chunking: split corpus documents into chunks with their positions."""

import sys
from pathlib import Path

from chonkie import RecursiveChunker, RecursiveLevel, RecursiveRules
from tqdm import tqdm

from src.config import RAW_DIR
from src.ingest import ingest
from src.models import Chunk, Document


def _chunk_doc(doc: Document,
               chunker: RecursiveChunker,
               max_chunk_size: int) -> list[Chunk]:
    """Split a document into chunks with the given chunker.

    The same function serves every file type: only the chunker changes.

    Args:
        doc: Document to split.
        chunker: Chunker built by ``_make_md_chunker`` or
            ``_make_py_chunker``, reused for every document.
        max_chunk_size: Maximum chunk length, in characters.

    Returns:
        The chunks in file order. Each one covers
        ``doc.content[first_char_i:last_char_i]``, end excluded.

    Raises:
        ValueError: If a chunk is longer than ``max_chunk_size``.
    """
    chunk_list: list[Chunk] = []
    for piece in chunker.chunk(doc.content):
        doc_chunk = Chunk(file_path=doc.file_path,
                          first_char_i=piece.start_index,
                          last_char_i=piece.end_index,
                          text=piece.text)
        size = doc_chunk.last_char_i - doc_chunk.first_char_i
        if size > max_chunk_size:
            raise ValueError(
                f"chunk too long in {doc.file_path} "
                f"[{doc_chunk.first_char_i}:{doc_chunk.last_char_i}]: "
                f"{size} > {max_chunk_size}")
        chunk_list.append(doc_chunk)
    return chunk_list


def _make_md_chunker(max_chunk_size: int) -> RecursiveChunker:
    """Build a chunker that follows the structure of Markdown files.

    It cuts at headings first, then at paragraphs, lines, sentences and
    words. The last level cuts at any character, so no chunk can be
    longer than ``max_chunk_size``. Headings go with the next chunk, so
    each section starts with its title.

    Args:
        max_chunk_size: Maximum chunk length, in characters.

    Returns:
        A chunker that counts sizes in characters.
    """
    level_1 = RecursiveLevel(delimiters=["\n# ", "\n## ", "\n### ", "\n#### "],
                             include_delim="next")
    level_2 = RecursiveLevel(delimiters=["\n\n"])
    level_3 = RecursiveLevel(delimiters=["\n"])
    level_4 = RecursiveLevel(delimiters=[". ", "! ", "? "])
    level_5 = RecursiveLevel(whitespace=True)
    level_6 = RecursiveLevel()

    rules = RecursiveRules(levels=[level_1, level_2, level_3,
                                   level_4, level_5, level_6])

    return RecursiveChunker(chunk_size=max_chunk_size, rules=rules)


def _make_py_chunker(max_chunk_size: int) -> RecursiveChunker:
    """Build a chunker that follows the structure of Python files.

    It cuts before top-level classes and functions first, then before
    methods (indented by 4 spaces), then at blank lines, lines and
    words. The last level cuts at any character, so no chunk can be
    longer than ``max_chunk_size``. A ``def`` or ``class`` line goes
    with the next chunk, so each function starts with its signature.
    Decorators stay at the end of the previous chunk.

    Args:
        max_chunk_size: Maximum chunk length, in characters.

    Returns:
        A chunker that counts sizes in characters.
    """
    level_1 = RecursiveLevel(delimiters=["\nclass ", "\ndef ", "\nasync def "],
                             include_delim="next")
    level_2 = RecursiveLevel(delimiters=["\n    def ", "\n    async def "],
                             include_delim="next")
    level_3 = RecursiveLevel(delimiters=["\n\n"])
    level_4 = RecursiveLevel(delimiters=["\n"])
    level_5 = RecursiveLevel(whitespace=True)
    level_6 = RecursiveLevel()

    rules = RecursiveRules(levels=[level_1, level_2, level_3,
                                   level_4, level_5, level_6])

    return RecursiveChunker(chunk_size=max_chunk_size, rules=rules)


def chunk_documents(docs: list[Document], max_chunk_size: int) -> list[Chunk]:
    """Split every document with the chunker that matches its file type.

    ``.md`` and ``.txt`` files use the Markdown chunker, ``.py`` files the
    Python chunker. Both chunkers are built once and reused. Files with
    another extension are skipped with a warning on stderr.

    Args:
        docs: Documents returned by ``ingest``.
        max_chunk_size: Maximum chunk length, in characters.

    Returns:
        All the chunks, document after document, in file order.

    Raises:
        ValueError: If a chunk is longer than ``max_chunk_size``.
    """
    md_chunker = _make_md_chunker(max_chunk_size)
    py_chunker = _make_py_chunker(max_chunk_size)
    chunker_dict: dict[str, RecursiveChunker] = {
        ".md": md_chunker,
        ".txt": md_chunker,
        ".py": py_chunker,
    }

    chunks_list: list[Chunk] = []
    for doc in tqdm(docs, desc="Chunking"):
        suffix = Path(doc.file_path).suffix
        chunker = chunker_dict.get(suffix)
        if chunker is None:
            print(f"Warning: no chunker for {doc.file_path}, skipped",
                  file=sys.stderr)
            continue
        chunks_list.extend(_chunk_doc(doc, chunker, max_chunk_size))
    return chunks_list


if __name__ == "__main__":
    # Temporary test: chunk the whole corpus and check every chunk.
    size_limit = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    all_docs = ingest(Path(RAW_DIR))
    content_of = {d.file_path: d.content for d in all_docs}
    chunks = chunk_documents(all_docs, size_limit)
    for c in chunks:
        assert content_of[c.file_path][c.first_char_i:c.last_char_i] == c.text
        assert c.last_char_i - c.first_char_i <= size_limit
    print(f"{len(all_docs)} documents -> {len(chunks)} chunks "
          f"(max {size_limit})")
