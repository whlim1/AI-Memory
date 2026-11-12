"""Tests for ai_memory_pipeline.semantic_summary."""

import pytest

from ai_memory_pipeline.semantic_summary import (
    SemanticSummarizer,
    summarize_text,
)


@pytest.fixture
def summarizer():
    return SemanticSummarizer()


class TestExtractKeywords:
    def test_non_string_returns_empty_list(self, summarizer):
        assert summarizer.extract_keywords(None) == []
        assert summarizer.extract_keywords(12345) == []

    def test_whitespace_only_returns_empty_list(self, summarizer):
        assert summarizer.extract_keywords("   \n\t ") == []

    def test_filters_stop_words_and_counts_frequency(self, summarizer):
        text = "apple banana apple cherry apple banana"
        # apple: 3, banana: 2, cherry: 1; stop words absent.
        assert summarizer.extract_keywords(text) == [
            "apple",
            "banana",
            "cherry",
        ]

    def test_punctuation_is_stripped(self, summarizer):
        # Punctuation is removed before tokenizing, so "AI," and "ai" merge.
        text = "AI, ai, AI!"
        assert summarizer.extract_keywords(text) == ["ai"]

    def test_respects_num_keywords_limit(self, summarizer):
        words = " ".join(f"w{i}" for i in range(10))
        result = summarizer.extract_keywords(words, num_keywords=3)
        assert len(result) == 3
        # most_common preserves insertion order on ties.
        assert result == ["w0", "w1", "w2"]

    def test_all_stop_words_returns_empty_list(self, summarizer):
        assert summarizer.extract_keywords("the a an and or but") == []


class TestScoreSentences:
    def test_empty_list_returns_empty_list(self, summarizer):
        assert summarizer.score_sentences([]) == []

    def test_first_and_last_get_position_bonus(self, summarizer):
        sentences = ["alpha beta", "gamma delta", "epsilon zeta"]
        scored = summarizer.score_sentences(sentences)
        # Each sentence contains 2 keywords; first/last get +2 bonus.
        assert scored[0] == (4, "alpha beta")
        assert scored[1] == (4, "epsilon zeta")
        assert scored[2] == (2, "gamma delta")

    def test_sorted_descending_by_score(self, summarizer):
        # Middle sentence has more keywords than the first.
        sentences = ["alpha", "beta gamma delta epsilon"]
        scored = summarizer.score_sentences(sentences)
        assert [score for score, _ in scored] == sorted(
            (score for score, _ in scored), reverse=True
        )
        # Middle sentence: 4 keywords + no bonus; first: 1 keyword + 2 bonus.
        assert scored[0][1] == "beta gamma delta epsilon"

    def test_single_sentence_gets_bonus(self, summarizer):
        scored = summarizer.score_sentences(["only one"])
        # "only" and "one" are not stop words -> 2 keyword matches; the +2
        # position bonus is applied once (i == 0 and i == len-1 coincide).
        assert scored == [(4, "only one")]


class TestGenerateSummary:
    def test_non_string_returns_empty_string(self, summarizer):
        assert summarizer.generate_summary(None) == ""
        assert summarizer.generate_summary(42) == ""

    def test_whitespace_only_returns_empty_string(self, summarizer):
        assert summarizer.generate_summary("   ") == ""

    def test_short_text_returned_as_is_without_punctuation(self, summarizer):
        # Fewer sentences than num_sentences -> joined stripped sentences.
        text = "One two three. Four five six."
        assert summarizer.generate_summary(text) == (
            "One two three Four five six"
        )

    def test_selects_top_scored_sentences(self, summarizer):
        # Five distinct sentences; summary must contain exactly 3 of them,
        # including the first sentence (position bonus).
        text = (
            "Alpha beta gamma. Delta epsilon zeta. Eta theta iota. "
            "Kappa lambda mu. Nu xi omicron."
        )
        summary = summarizer.generate_summary(text, num_sentences=3)
        parts = [p for p in summary.split(" ") if p]
        # Reconstruct: 3 sentences x 3 words each, joined by single spaces.
        assert len(parts) == 9
        assert "Alpha beta gamma" in summary

    def test_summary_never_longer_than_input_sentence_count(self, summarizer):
        text = "a b c. d e f. g h i. j k l."
        summary = summarizer.generate_summary(text, num_sentences=2)
        # Exactly the top 2 sentences (3 words each).
        assert len(summary.split()) == 6


class TestGenerateKeywordSummary:
    def test_non_string_returns_empty_string(self, summarizer):
        assert summarizer.generate_keyword_summary(None) == ""

    def test_whitespace_only_returns_empty_string(self, summarizer):
        assert summarizer.generate_keyword_summary("   ") == ""

    def test_formats_key_topics_line(self, summarizer):
        text = "apple banana apple cherry"
        result = summarizer.generate_keyword_summary(text, num_keywords=2)
        assert result == "Key topics: apple, banana"

    def test_empty_text_yields_bare_prefix(self, summarizer):
        # No keywords -> empty join.
        assert summarizer.generate_keyword_summary("the and a") == (
            "Key topics: "
        )


class TestSummarizeTextDispatcher:
    def test_default_method_is_semantic(self):
        text = "One two three. Four five six."
        expected = SemanticSummarizer().generate_summary(text, 3)
        assert summarize_text(text) == expected

    def test_keywords_method_dispatches(self):
        text = "apple banana apple cherry"
        result = summarize_text(text, method="keywords", num_keywords=2)
        assert result == "Key topics: apple, banana"

    def test_semantic_method_accepts_num_sentences_kwarg(self):
        text = "a b c. d e f. g h i."
        expected = SemanticSummarizer().generate_summary(text, 1)
        assert summarize_text(text, method="semantic", num_sentences=1) == (
            expected
        )

    def test_unknown_method_raises_value_error(self):
        with pytest.raises(ValueError, match=r"Unknown summary method: bogus"):
            summarize_text("hello world", method="bogus")
