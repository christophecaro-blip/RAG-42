"""Tokenization: turn a text into search terms for BM25.

The same function is used for the chunks (indexing) and for the questions
(search), so that both sides produce comparable terms.
"""

import re

from bm25s.stopwords import STOPWORDS_EN

from src.config import REMOVE_STOPWORDS

_WORD_RE = re.compile(r"[A-Za-z0-9_]+")
_CAMEL_RE = re.compile(
    r"[A-Z]{2,}(?=s(?![a-z]))"    # plural acronym: GPU in GPUs
    r"|[A-Z]+(?=[A-Z][a-z])"      # acronym before a word: LLM in LLMEngine
    r"|[A-Z]?[a-z]+[0-9]*"        # word with its digits: Engine, Qwen3
    r"|[A-Z]+[0-9]*"              # acronym with its digits: HTTP, FP8
    r"|[0-9]+"                    # number alone: 2048
)
_STOPWORDS = frozenset(STOPWORDS_EN)


def _split_camel(word: str) -> list[str]:
    """Split a word at its case changes.

    A run of capitals followed by a word gives its last capital to that
    word (``LLMEngine`` -> ``LLM``, ``Engine``). Digits stay attached to
    the letters before them (``FP8``, ``Qwen3``). A plural acronym keeps
    its acronym whole (``GPUs`` -> ``GPU``, ``s``).

    Args:
        word: Word without underscores (e.g. ``"getHTTPResponse"``).

    Returns:
        The pieces in order, with their original case
        (e.g. ``["get", "HTTP", "Response"]``).
    """
    return _CAMEL_RE.findall(word)


def _split_snake(word: str) -> list[str]:
    """Split a word at its underscores.

    Leading, trailing and repeated underscores give no empty piece.

    Args:
        word: Word that may contain underscores (e.g. ``"__init__"``).

    Returns:
        The non-empty pieces in order (e.g. ``["init"]``).
    """
    parts: list[str] = []
    for part in word.split('_'):
        if part:
            parts.append(part)
    return parts


def tokenize(text: str,
             remove_stopwords: bool = REMOVE_STOPWORDS) -> list[str]:
    """Turn a text into lowercase search terms.

    Each word is kept whole, and is also split into its snake_case and
    CamelCase pieces when it has more than one
    (``enable_lora`` -> ``enable_lora``, ``enable``, ``lora``).
    One-letter terms are always removed.

    Args:
        text: Text to tokenize (a chunk or a question).
        remove_stopwords: Whether to remove common English words
            (``the``, ``of``, ``in``...). The default comes from
            ``config.py``, so indexing and search stay consistent.

    Returns:
        The terms in text order. A term repeated in the text is repeated
        in the result, since BM25 counts occurrences.
    """
    words = _WORD_RE.findall(text)

    terms: list[str] = []
    for word in words:
        parts: list[str] = []
        for part in _split_snake(word):
            parts.extend(_split_camel(part))
        terms.append(word.lower())
        if len(parts) > 1:
            terms.extend(p.lower() for p in parts)
    filtered = [t for t in terms
                if len(t) > 1
                and (t not in _STOPWORDS or not remove_stopwords)]
    return filtered


if __name__ == "__main__":
    # Temporary tests: compare each case with its expected result.
    snake_cases = {
        "trust_remote_code": ["trust", "remote", "code"],
        "__init__": ["init"],
        "a__b": ["a", "b"],
        "LLMEngine": ["LLMEngine"],
        "___": [],
    }
    camel_cases = {
        "LLMEngine": ["LLM", "Engine"],
        "getHTTPResponse": ["get", "HTTP", "Response"],
        "enable": ["enable"],
        "FP8": ["FP8"],
        "vLLM": ["v", "LLM"],
        "Llama2Model": ["Llama2", "Model"],
        "GPUs": ["GPU", "s"],
        "IDs": ["ID", "s"],
        "GPUsAvailable": ["GPU", "s", "Available"],
        "Users": ["Users"],
    }
    for func, cases in ((_split_snake, snake_cases),
                        (_split_camel, camel_cases)):
        for word, expected in cases.items():
            result = func(word)
            status = "OK " if result == expected else "BAD"
            print(f"{status} {func.__name__}({word!r}) -> {result}")

    for text in ("How does LLMEngine handle enable_lora?",
                 "What's the default value of trust_remote_code "
                 "in vLLM's LLM class?",
                 "How many GPUs and IDs?",
                 ""):
        print(f"tokenize({text!r})\n    -> {tokenize(text)}")
