"""Pydantic data models exchanged between the RAG stages."""

import uuid
from typing import List

from pydantic import BaseModel, Field


class MinimalSource(BaseModel):
    """A character range inside one file of the corpus."""

    file_path: str
    first_character_index: int
    last_character_index: int


class UnansweredQuestion(BaseModel):
    """A question without its expected answer."""

    question_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str


class AnsweredQuestion(UnansweredQuestion):
    """A question with its ground-truth sources and answer."""

    sources: List[MinimalSource]
    answer: str


class RagDataset(BaseModel):
    """A dataset of RAG questions, answered or not."""

    rag_questions: List[AnsweredQuestion | UnansweredQuestion]


class MinimalSearchResults(BaseModel):
    """The sources retrieved for one question."""

    question_id: str
    question: str
    retrieved_sources: List[MinimalSource]


class MinimalAnswer(MinimalSearchResults):
    """The sources retrieved for one question, plus the generated answer."""

    answer: str


class StudentSearchResults(BaseModel):
    """Output of the search_dataset command."""

    search_results: List[MinimalSearchResults]
    k: int


class StudentSearchResultsAndAnswer(BaseModel):
    """Output of the answer_dataset command."""

    search_results: List[MinimalAnswer]
    k: int


class Document(BaseModel):
    """One corpus file: its path as written in the sources, and its text."""

    file_path: str
    content: str


class Chunk(BaseModel):
    """A piece of a corpus file, with its position in that file."""

    file_path: str
    first_char_i: int
    last_char_i: int
    text: str


class IndexMetadata(BaseModel):
    """What the index command saves next to the BM25 index.

    ``chunks[i]`` is the chunk of result ``i`` of a search on the index.
    """

    max_chunk_size: int
    remove_stopwords: bool
    chunks: list[Chunk]
