"""Indexing: build the BM25 index of the corpus chunks."""

from pathlib import Path

import bm25s

from src.chunking import chunk_documents
from src.config import PROCESSED_DIR, RAW_DIR, REMOVE_STOPWORDS
from src.ingest import ingest
from src.models import Chunk, IndexMetadata
from src.tokenizer import tokenize

_BM25_DIR = Path(PROCESSED_DIR) / "bm25"
_METADATA_PATH = Path(PROCESSED_DIR) / "index.json"


def build_index(max_chunk_size: int) -> tuple[bm25s.BM25, list[Chunk]]:
    """Read, chunk and tokenize the corpus, index it with BM25 and save it.

    Saved in ``PROCESSED_DIR``: the BM25 index in ``bm25/``, and in
    ``index.json`` the settings used and the chunks, in index order.

    Args:
        max_chunk_size: Maximum chunk length, in characters.

    Returns:
        The BM25 index and the chunks, in the same order: result ``i``
        of a search on the index is ``chunks[i]``.
    """
    docs = ingest(Path(RAW_DIR))
    chunks = chunk_documents(docs, max_chunk_size)
    corpus_tokens = [tokenize(c.text) for c in chunks]

    retriever = bm25s.BM25()
    retriever.index(corpus_tokens)

    metadata_path = _METADATA_PATH
    _BM25_DIR.mkdir(parents=True, exist_ok=True)

    retriever.save(str(_BM25_DIR))
    metadata = IndexMetadata(max_chunk_size=max_chunk_size,
                             remove_stopwords=REMOVE_STOPWORDS,
                             chunks=chunks)
    metadata_path.write_text(metadata.model_dump_json(), encoding="utf-8")

    return retriever, chunks


def load_index() -> tuple[bm25s.BM25, IndexMetadata]:
    """Load the index saved by ``build_index``.

    Returns:
        The BM25 index and its metadata, in the same order as
        ``build_index``: result ``i`` of a search is ``metadata.chunks[i]``.

    Raises:
        FileNotFoundError: If the index, or part of it, is missing from
            ``PROCESSED_DIR``.
    """
    try:
        index = bm25s.BM25.load(str(_BM25_DIR), show_progress=False)
        read_data = _METADATA_PATH.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"No index found in {PROCESSED_DIR}/: "
            "run the 'index' command first.") from e

    metadata = IndexMetadata.model_validate_json(read_data)

    return index, metadata
