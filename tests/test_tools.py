"""
Unit tests for src/tools/text_tools.py
"""

import pytest

from src.tools.text_tools import get_text_statistics, summarize_text


# ---------------------------------------------------------------------------
# summarize_text
# ---------------------------------------------------------------------------


class TestSummarizeText:
    SAMPLE = (
        "The quick brown fox jumps over the lazy dog. "
        "This sentence is often used for testing typography. "
        "It contains every letter of the English alphabet. "
        "Typographers love this pangram for its completeness. "
        "Dogs and foxes both appear in the classic phrase."
    )

    def test_returns_dict_with_expected_keys(self):
        result = summarize_text(self.SAMPLE)
        assert isinstance(result, dict)
        for key in ("summary", "original_length", "summary_length", "compression_ratio"):
            assert key in result, f"Missing key: {key}"

    def test_summary_is_shorter_than_original(self):
        result = summarize_text(self.SAMPLE, max_sentences=2)
        assert result["summary_length"] <= result["original_length"]

    def test_compression_ratio_between_0_and_1(self):
        result = summarize_text(self.SAMPLE, max_sentences=2)
        assert 0.0 < result["compression_ratio"] <= 1.0

    def test_original_length_matches_input(self):
        result = summarize_text(self.SAMPLE)
        assert result["original_length"] == len(self.SAMPLE)

    def test_max_sentences_respected(self):
        result = summarize_text(self.SAMPLE, max_sentences=2)
        # A rough check: the summary should not contain more sentences than requested
        sentences_in_summary = [s for s in result["summary"].split(". ") if s.strip()]
        assert len(sentences_in_summary) <= 3  # allow slight heuristic leeway

    def test_single_sentence_input(self):
        text = "This is a single sentence."
        result = summarize_text(text)
        assert result["summary"] == text

    def test_empty_string_returns_error(self):
        result = summarize_text("")
        assert "error" in result

    def test_whitespace_only_returns_error(self):
        result = summarize_text("   ")
        assert "error" in result

    def test_non_string_returns_error(self):
        result = summarize_text(None)  # type: ignore[arg-type]
        assert "error" in result

    def test_max_sentences_clamped_to_minimum(self):
        result = summarize_text(self.SAMPLE, max_sentences=0)
        assert result.get("error") is None  # 0 is clamped to 1, not an error

    def test_max_sentences_clamped_to_maximum(self):
        result = summarize_text(self.SAMPLE, max_sentences=100)
        assert result.get("error") is None


# ---------------------------------------------------------------------------
# get_text_statistics
# ---------------------------------------------------------------------------


class TestGetTextStatistics:
    SAMPLE = (
        "Hello world. This is a test.\n\n"
        "Second paragraph here. It has two sentences."
    )

    def test_returns_dict_with_expected_keys(self):
        result = get_text_statistics(self.SAMPLE)
        expected_keys = {
            "character_count",
            "word_count",
            "sentence_count",
            "paragraph_count",
            "average_word_length",
            "average_sentence_length",
        }
        assert expected_keys.issubset(result.keys())

    def test_character_count_matches_len(self):
        result = get_text_statistics(self.SAMPLE)
        assert result["character_count"] == len(self.SAMPLE)

    def test_word_count_positive(self):
        result = get_text_statistics(self.SAMPLE)
        assert result["word_count"] > 0

    def test_sentence_count_positive(self):
        result = get_text_statistics(self.SAMPLE)
        assert result["sentence_count"] > 0

    def test_paragraph_count_correct(self):
        result = get_text_statistics(self.SAMPLE)
        assert result["paragraph_count"] == 2

    def test_average_word_length_positive(self):
        result = get_text_statistics(self.SAMPLE)
        assert result["average_word_length"] > 0.0

    def test_average_sentence_length_positive(self):
        result = get_text_statistics(self.SAMPLE)
        assert result["average_sentence_length"] > 0.0

    def test_empty_string_returns_error(self):
        result = get_text_statistics("")
        assert "error" in result

    def test_whitespace_only_returns_error(self):
        result = get_text_statistics("   \n  ")
        assert "error" in result

    def test_non_string_returns_error(self):
        result = get_text_statistics(42)  # type: ignore[arg-type]
        assert "error" in result

    def test_single_word(self):
        result = get_text_statistics("Hello.")
        assert result["word_count"] == 1
        assert result["sentence_count"] == 1
