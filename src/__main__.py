"""Command-line interface of the RAG system.

Run with ``uv run python -m src <command> [options]``.
"""

import inspect
import sys
from typing import Annotated, List

import fire
from pydantic import (
    FilePath,
    Field,
    StringConstraints,
    ValidationError,
    validate_call,
)


ChunkSize = Annotated[int, Field(ge=1, le=2000, strict=True)]
K = Annotated[int, Field(ge=1, le=10, strict=True)]
Query = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class CLI:
    """Commands of the RAG pipeline: index, search, answer and evaluate."""

    @validate_call
    def index(self, max_chunk_size: ChunkSize = 2000) -> None:
        """Ingest data/raw/ and build the index under data/processed/.

        Args:
            max_chunk_size: Maximum chunk length in characters (1 to 2000).
        """
        pass

    @validate_call
    def search(self, query: Query, k: K = 10) -> None:
        """Return the top-k sources for a single query.

        Args:
            query: The question to search for.
            k: Number of sources to return (1 to 10).
        """
        pass

    @validate_call
    def search_dataset(self,
                       dataset_path: FilePath,
                       save_directory: str,
                       k: K = 10) -> None:
        """Search a whole dataset and save a StudentSearchResults file.

        Args:
            dataset_path: Path to the questions dataset JSON.
            save_directory: Directory where the results are written.
            k: Number of sources per question (1 to 10).
        """
        pass

    @validate_call
    def answer(self, query: Query, k: K = 10) -> None:
        """Answer a single query using the retrieved context.

        Args:
            query: The question to answer.
            k: Number of sources used as context (1 to 10).
        """
        pass

    @validate_call
    def answer_dataset(self,
                       student_search_results_path: FilePath,
                       save_directory: str) -> None:
        """Generate answers and save a StudentSearchResultsAndAnswer file.

        Args:
            student_search_results_path: Output file of search_dataset.
            save_directory: Directory where the answers are written.
        """
        pass

    @validate_call
    def evaluate(self,
                 student_search_results_path: FilePath,
                 dataset_path: FilePath) -> None:
        """Report recall@k against a ground-truth dataset.

        Args:
            student_search_results_path: Output file of search_dataset.
            dataset_path: AnsweredQuestions dataset JSON (ground truth).
        """
        pass


def _param_names(command: str) -> List[str]:
    """Return the parameter names of a CLI command, ``self`` included.

    Fire passes arguments by position, so pydantic reports an error
    location as an index; this list turns that index back into a name.

    Args:
        command: Name of the CLI method (e.g. ``"search"``).

    Returns:
        The parameter names, or an empty list if the command is unknown.
    """
    method = getattr(CLI, command, None)
    if method is None:
        return []
    return list(inspect.signature(method).parameters)


if __name__ == "__main__":
    try:
        fire.Fire(CLI)
    except ValidationError as err:
        names = _param_names(sys.argv[1]) if len(sys.argv) > 1 else []
        for e in err.errors():
            where = e["loc"][0] if e["loc"] else "?"
            if isinstance(where, int) and where < len(names):
                where = names[where]
            print(f"Error: --{where}={e['input']!r}: {e['msg']}",
                  file=sys.stderr)
        sys.exit(1)
