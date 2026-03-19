"""
Text tools for the AI summarization agent.

These tools are registered with the ADK agent and can be called
during inference to perform text operations.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def summarize_text(text: str, max_sentences: int = 3) -> dict[str, Any]:
    """Summarize the provided text by extracting the most important sentences.

    This tool uses extractive summarization: it scores each sentence by
    word-frequency and returns the top-ranked sentences as the summary.

    Args:
        text: The input text to summarize.
        max_sentences: Maximum number of sentences to include in the summary.
                       Must be between 1 and 10.

    Returns:
        A dictionary with keys:
            - ``summary`` (str): The extracted summary.
            - ``original_length`` (int): Character count of the input.
            - ``summary_length`` (int): Character count of the summary.
            - ``compression_ratio`` (float): summary_length / original_length.
    """
    if not isinstance(text, str) or not text.strip():
        return {
            "error": "Input text must be a non-empty string.",
            "summary": "",
            "original_length": 0,
            "summary_length": 0,
            "compression_ratio": 0.0,
        }

    max_sentences = max(1, min(10, int(max_sentences)))

    sentences = _split_sentences(text)
    if not sentences:
        return {
            "summary": text.strip(),
            "original_length": len(text),
            "summary_length": len(text.strip()),
            "compression_ratio": 1.0,
        }

    word_freq = _word_frequency(text)
    scores = {i: _score_sentence(s, word_freq) for i, s in enumerate(sentences)}
    top_indices = sorted(
        sorted(scores, key=scores.get, reverse=True)[:max_sentences]
    )
    summary = " ".join(sentences[i] for i in top_indices)

    original_length = len(text)
    summary_length = len(summary)
    compression_ratio = round(summary_length / original_length, 4) if original_length else 0.0

    logger.info(
        "summarize_text: %d chars -> %d chars (ratio %.2f)",
        original_length,
        summary_length,
        compression_ratio,
    )
    return {
        "summary": summary,
        "original_length": original_length,
        "summary_length": summary_length,
        "compression_ratio": compression_ratio,
    }


def get_text_statistics(text: str) -> dict[str, Any]:
    """Compute basic statistics for the provided text.

    Args:
        text: The input text to analyse.

    Returns:
        A dictionary with keys:
            - ``character_count`` (int): Total characters.
            - ``word_count`` (int): Total words.
            - ``sentence_count`` (int): Total sentences.
            - ``paragraph_count`` (int): Total paragraphs.
            - ``average_word_length`` (float): Mean word length.
            - ``average_sentence_length`` (float): Mean words per sentence.
    """
    if not isinstance(text, str) or not text.strip():
        return {
            "error": "Input text must be a non-empty string.",
            "character_count": 0,
            "word_count": 0,
            "sentence_count": 0,
            "paragraph_count": 0,
            "average_word_length": 0.0,
            "average_sentence_length": 0.0,
        }

    words = re.findall(r"\b\w+\b", text)
    sentences = _split_sentences(text)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    word_count = len(words)
    sentence_count = len(sentences)

    avg_word_length = (
        round(sum(len(w) for w in words) / word_count, 2) if word_count else 0.0
    )
    avg_sentence_length = (
        round(word_count / sentence_count, 2) if sentence_count else 0.0
    )

    stats = {
        "character_count": len(text),
        "word_count": word_count,
        "sentence_count": sentence_count,
        "paragraph_count": len(paragraphs),
        "average_word_length": avg_word_length,
        "average_sentence_length": avg_sentence_length,
    }
    logger.info("get_text_statistics: %s", stats)
    return stats


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _split_sentences(text: str) -> list[str]:
    """Split *text* into sentences using a simple regex heuristic."""
    raw = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in raw if s.strip()]


def _word_frequency(text: str) -> dict[str, int]:
    """Return a lower-cased word-frequency map, ignoring common stop-words."""
    stop_words = {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to",
        "for", "of", "with", "by", "from", "is", "it", "be", "as",
        "this", "that", "was", "are", "were", "been", "have", "has", "had",
        "not", "we", "they", "he", "she", "i", "you", "do", "did",
        "will", "would", "can", "could", "may", "might", "its", "their",
        "our", "your", "his", "her", "so", "if", "then", "than", "when",
        "up", "out", "no", "more", "also", "into", "about",
    }
    freq: dict[str, int] = {}
    for word in re.findall(r"\b\w+\b", text.lower()):
        if word not in stop_words:
            freq[word] = freq.get(word, 0) + 1
    return freq


def _score_sentence(sentence: str, word_freq: dict[str, int]) -> float:
    """Score a sentence by the sum of its word frequencies."""
    words = re.findall(r"\b\w+\b", sentence.lower())
    return sum(word_freq.get(w, 0) for w in words)
