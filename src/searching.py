"""Searching: find the best chunks of the index for some questions."""

from bm25s import BM25

from src.models import Chunk, IndexMetadata
from src.tokenizer import tokenize


def search_chunks(retriever: BM25, metadata: IndexMetadata,
                  queries: list[str],
                  k: int) -> list[list[tuple[Chunk, float]]]:
    """Search the index for each question and return its top-k chunks.

    Nothing is printed: each command formats the results its own way.

    Args:
        retriever: The BM25 index, loaded once by the caller.
        metadata: The index metadata (chunks and indexing settings).
        queries: The questions to search for, all in one batch.
        k: Number of chunks to return per question.

    Returns:
        One list per question, in the order of ``queries``, holding its
        ``k`` best ``(chunk, score)`` pairs, best first.
    """
    tokens = [tokenize(q, remove_stopwords=metadata.remove_stopwords)
              for q in queries]
    chunk_ids, scores = retriever.retrieve(tokens, k=k, show_progress=False)
    results: list[list[tuple[Chunk, float]]] = []
    for question_ids, question_scores in zip(chunk_ids, scores):
        question_results = []
        for chunk_id, score in zip(question_ids, question_scores):
            question_results.append((metadata.chunks[chunk_id], float(score)))
        results.append(question_results)
    return results
