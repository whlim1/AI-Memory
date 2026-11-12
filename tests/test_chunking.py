"""Tests for ai_memory_pipeline.chunking."""

import pytest

from ai_memory_pipeline.chunking import (
    chunk_generator,
    chunk_text,
    split_text_by_paragraphs,
    split_text_by_sentences,
    split_text_by_words,
)


class TestSplitTextBySentences:
    def test_empty_string_returns_empty_list(self):
        assert split_text_by_sentences("") == []

    def test_non_string_input_returns_empty_list(self):
        assert split_text_by_sentences(None) == []
        assert split_text_by_sentences(12345) == []

    def test_single_sentence_strips_punctuation(self):
        # The regex [.!?]+ removes terminal punctuation from sentences.
        assert split_text_by_sentences("Hello world.") == ["Hello world"]

    def test_multiple_sentences_joined_when_under_limit(self):
        text = "One two three. Four five six."
        chunks = split_text_by_sentences(text, max_chunk_size=30)
        assert chunks == ["One two three Four five six"]

    def test_splits_into_new_chunk_on_overflow(self):
        # Each sentence is 13 chars; 13 + 13 + 1 = 27 > 25 -> split.
        text = "One two three. Four five six."
        chunks = split_text_by_sentences(text, max_chunk_size=25)
        assert chunks == ["One two three", "Four five six"]

    def test_multiple_punctuation_marks_collapse(self):
        # [.!?]+ treats runs of punctuation as a single separator.
        text = "First!! Second? Third."
        chunks = split_text_by_sentences(text, max_chunk_size=100)
        assert chunks == ["First Second Third"]

    def test_no_punctuation_is_single_chunk(self):
        assert split_text_by_sentences("no punctuation here") == [
            "no punctuation here"
        ]

    def test_chunks_respect_max_size_when_sentences_fit(self):
        text = "aa bb cc. dd ee ff. gg hh ii."
        chunks = split_text_by_sentences(text, max_chunk_size=10)
        assert all(len(c) <= 10 for c in chunks)
        # Rejoining with spaces reconstructs the stripped sentences.
        assert " ".join(chunks).split() == text.replace(".", "").split()


class TestSplitTextByWords:
    def test_empty_string_returns_empty_list(self):
        assert split_text_by_words("") == []

    def test_non_string_input_returns_empty_list(self):
        assert split_text_by_words(None) == []
        assert split_text_by_words(["a", "b"]) == []

    def test_groups_words_up_to_limit(self):
        # 26 two-letter words; limit 10 fits exactly three per chunk (8 chars).
        text = " ".join(f"{c}{c}" for c in "abcdefghijklmnopqrstuvwxyz")
        chunks = split_text_by_words(text, max_chunk_size=10)
        assert chunks == [
            "aa bb cc",
            "dd ee ff",
            "gg hh ii",
            "jj kk ll",
            "mm nn oo",
            "pp qq rr",
            "ss tt uu",
            "vv ww xx",
            "yy zz",
        ]

    def test_single_word_longer_than_limit_is_its_own_chunk(self):
        # No hard splitting: an oversized word still becomes a chunk.
        assert split_text_by_words("abcdefghij k", max_chunk_size=5) == [
            "abcdefghij",
            "k",
        ]

    def test_whitespace_only_returns_empty_list(self):
        assert split_text_by_words("   \n\t  ") == []


class TestSplitTextByParagraphs:
    def test_empty_string_returns_empty_list(self):
        assert split_text_by_paragraphs("") == []

    def test_non_string_input_returns_empty_list(self):
        assert split_text_by_paragraphs(42) == []

    def test_joins_paragraphs_with_blank_line_when_under_limit(self):
        text = "para one\n\npara two"
        chunks = split_text_by_paragraphs(text, max_chunk_size=30)
        assert chunks == ["para one\n\npara two"]

    def test_splits_on_overflow_using_two_char_joiner(self):
        # 8 + 10 + 2 = 20 <= 25 -> join; then 18 + 8 + 2 = 28 > 25 -> split.
        text = "para one\n\nlonger para two\n\nthree"
        chunks = split_text_by_paragraphs(text, max_chunk_size=25)
        assert chunks == ["para one\n\nlonger para two", "three"]

    def test_blank_paragraphs_are_skipped(self):
        text = "\n\nfirst\n\n\n\nsecond\n\n"
        chunks = split_text_by_paragraphs(text, max_chunk_size=100)
        assert chunks == ["first\n\nsecond"]


class TestChunkText:
    def test_default_method_is_sentences(self):
        text = "One two three. Four five six."
        assert chunk_text(text) == split_text_by_sentences(
            text, max_chunk_size=1000
        )

    def test_dispatches_to_words(self):
        text = "aa bb cc dd"
        assert chunk_text(text, method="words", max_chunk_size=6) == [
            "aa bb",
            "cc dd",
        ]

    def test_dispatches_to_paragraphs(self):
        text = "one\n\ntwo"
        assert chunk_text(text, method="paragraphs") == ["one\n\ntwo"]

    def test_unknown_method_raises_value_error(self):
        with pytest.raises(ValueError, match=r"Unknown chunking method: bogus"):
            chunk_text("hello", method="bogus")


class TestChunkGenerator:
    def test_yields_same_chunks_as_chunk_text(self):
        text = "aa bb cc. dd ee ff. gg hh ii."
        expected = chunk_text(text, method="sentences", max_chunk_size=10)
        assert list(chunk_generator(text, method="sentences", max_chunk_size=10)) == expected

    def test_is_lazy(self):
        # The generator object is returned without evaluating the text.
        gen = chunk_generator("anything at all")
        assert not isinstance(gen, list)
        assert next(gen) == "anything at all"
