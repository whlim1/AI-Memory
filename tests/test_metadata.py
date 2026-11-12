"""Tests for ai_memory_pipeline.metadata."""

import hashlib
from datetime import datetime as real_datetime, timedelta

import pytest

import ai_memory_pipeline.metadata as metadata_module
from ai_memory_pipeline.metadata import (
    DocumentMetadata,
    extract_metadata_from_text,
    merge_metadata,
)


class _FixedDatetime(real_datetime):
    """datetime subclass with a frozen clock for deterministic IDs."""

    @classmethod
    def now(cls, tz=None):
        return cls(2024, 1, 15, 12, 30, 45)


FIXED_NOW = _FixedDatetime(2024, 1, 15, 12, 30, 45)
EXPECTED_ID = hashlib.md5(str(FIXED_NOW.timestamp()).encode()).hexdigest()[:12]


@pytest.fixture
def fixed_clock(monkeypatch):
    monkeypatch.setattr(metadata_module, "datetime", _FixedDatetime)


@pytest.fixture
def advancing_clock(monkeypatch):
    """Clock that advances one second on every now() call."""
    ticks = {"n": 0}

    class _AdvancingDatetime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            ticks["n"] += 1
            return real_datetime(2024, 1, 15, 12, 30, 45) + timedelta(seconds=ticks["n"])

    monkeypatch.setattr(metadata_module, "datetime", _AdvancingDatetime)


class TestInit:
    def test_defaults(self, fixed_clock):
        meta = DocumentMetadata()
        assert meta.doc_id == EXPECTED_ID
        assert meta.title == ""
        assert meta.author == ""
        assert meta.source == ""
        assert meta.tags == []
        assert meta.custom_fields == {}
        assert meta.created_at == FIXED_NOW
        assert meta.updated_at == FIXED_NOW

    def test_explicit_doc_id_is_kept(self):
        meta = DocumentMetadata(doc_id="my-id")
        assert meta.doc_id == "my-id"

    def test_generated_id_format(self, fixed_clock):
        # md5 hexdigest truncated to 12 chars.
        assert len(DocumentMetadata().doc_id) == 12
        int(DocumentMetadata().doc_id, 16)  # must be valid hex

    def test_same_timestamp_yields_same_id(self, fixed_clock):
        # _generate_id depends only on the timestamp string, so a frozen
        # clock produces identical IDs (collision weakness documented here).
        assert DocumentMetadata().doc_id == DocumentMetadata().doc_id

    def test_tags_and_custom_fields_are_not_shared_between_instances(
        self, fixed_clock
    ):
        a = DocumentMetadata()
        b = DocumentMetadata()
        a.tags.append("x")
        a.custom_fields["k"] = 1
        assert b.tags == []
        assert b.custom_fields == {}


class TestToDictFromDict:
    def test_to_dict_keys_and_isoformat(self, fixed_clock):
        meta = DocumentMetadata(
            doc_id="d1", title="T", author="A", source="S", tags=["t"]
        )
        d = meta.to_dict()
        assert set(d) == {
            "doc_id",
            "title",
            "author",
            "created_at",
            "updated_at",
            "source",
            "tags",
            "custom_fields",
        }
        assert d["created_at"] == FIXED_NOW.isoformat()
        assert d["updated_at"] == FIXED_NOW.isoformat()

    def test_round_trip_preserves_fields(self, fixed_clock):
        meta = DocumentMetadata(
            doc_id="d1", title="T", author="A", source="S", tags=["t"],
            custom_fields={"k": "v"},
        )
        restored = DocumentMetadata.from_dict(meta.to_dict())
        assert restored.doc_id == "d1"
        assert restored.title == "T"
        assert restored.author == "A"
        assert restored.source == "S"
        assert restored.tags == ["t"]
        assert restored.custom_fields == {"k": "v"}
        assert restored.created_at == FIXED_NOW
        assert restored.updated_at == FIXED_NOW

    def test_from_dict_missing_timestamps_defaults_to_now(self, fixed_clock):
        restored = DocumentMetadata.from_dict({"doc_id": "d1"})
        assert restored.doc_id == "d1"
        assert isinstance(restored.created_at, real_datetime)
        assert isinstance(restored.updated_at, real_datetime)

    def test_from_dict_missing_doc_id_generates_new_one(self, fixed_clock):
        restored = DocumentMetadata.from_dict({"title": "T"})
        assert restored.doc_id == EXPECTED_ID  # generated from frozen clock


class TestUpdate:
    def test_updates_known_fields_and_bumps_updated_at(self, advancing_clock):
        meta = DocumentMetadata(doc_id="d1")
        old_updated = meta.updated_at
        meta.update(title="New", source="src")
        assert meta.title == "New"
        assert meta.source == "src"
        # update() re-reads the clock; with an advancing fake it must be later.
        assert meta.updated_at > old_updated

    def test_unknown_kwargs_are_ignored(self, fixed_clock):
        meta = DocumentMetadata(doc_id="d1")
        meta.update(bogus_field=42)
        assert not hasattr(meta, "bogus_field")

    def test_empty_update_still_bumps_updated_at(self, advancing_clock):
        meta = DocumentMetadata(doc_id="d1")
        old = meta.updated_at
        meta.update()
        assert meta.updated_at > old


class TestTags:
    def test_add_tag_appends_once(self, fixed_clock):
        meta = DocumentMetadata(doc_id="d1")
        meta.add_tag("a")
        meta.add_tag("b")
        meta.add_tag("a")  # duplicate ignored
        assert meta.tags == ["a", "b"]

    def test_remove_tag_removes_if_present(self, fixed_clock):
        meta = DocumentMetadata(doc_id="d1", tags=["a", "b"])
        meta.remove_tag("a")
        assert meta.tags == ["b"]

    def test_remove_missing_tag_is_noop(self, fixed_clock):
        meta = DocumentMetadata(doc_id="d1", tags=["a"])
        meta.remove_tag("zzz")  # must not raise
        assert meta.tags == ["a"]


class TestCustomFields:
    def test_add_and_remove_custom_field(self, fixed_clock):
        meta = DocumentMetadata(doc_id="d1")
        meta.add_custom_field("k", "v")
        assert meta.custom_fields["k"] == "v"
        meta.remove_custom_field("k")
        assert meta.custom_fields == {}

    def test_remove_missing_custom_field_is_noop(self, fixed_clock):
        meta = DocumentMetadata(doc_id="d1")
        meta.remove_custom_field("nope")  # must not raise KeyError


class TestExtractMetadataFromText:
    def test_empty_text_uses_defaults(self):
        meta = extract_metadata_from_text("")
        assert meta.title == "Untitled Document"
        assert meta.author == "Unknown Author"

    def test_first_line_becomes_title(self):
        meta = extract_metadata_from_text("My Title\nbody text")
        assert meta.title == "My Title"
        assert meta.author == "Unknown Author"

    def test_hash_prefixed_first_line_is_skipped(self):
        meta = extract_metadata_from_text("# Heading\nreal body")
        assert meta.title == "Untitled Document"

    def test_long_first_line_truncated_with_ellipsis(self):
        long_line = "x" * 60
        meta = extract_metadata_from_text(long_line + "\nbody")
        assert meta.title == ("x" * 50) + "..."

    def test_title_is_raw_line_without_stripping(self):
        # Quirk: only the '#' check strips; the title keeps leading spaces.
        meta = extract_metadata_from_text("   Padded Title\nbody")
        assert meta.title == "   Padded Title"

    def test_doc_id_passthrough(self):
        meta = extract_metadata_from_text("text", doc_id="abc123")
        assert meta.doc_id == "abc123"


class TestMergeMetadata:
    def test_returns_new_object_not_base(self, fixed_clock):
        base = DocumentMetadata(doc_id="d1", title="Base")
        merged = merge_metadata(base, {"title": "Merged"})
        assert merged is not base
        assert base.title == "Base"  # base untouched

    def test_copies_base_fields(self, fixed_clock):
        base = DocumentMetadata(
            doc_id="d1", title="T", author="A", source="S", tags=["x"]
        )
        merged = merge_metadata(base, {})
        assert merged.doc_id == "d1"
        assert merged.title == "T"
        assert merged.author == "A"
        assert merged.source == "S"
        assert merged.tags == ["x"]

    def test_additional_known_fields_override(self, fixed_clock):
        base = DocumentMetadata(doc_id="d1", title="Base")
        merged = merge_metadata(base, {"title": "New", "source": "src"})
        assert merged.title == "New"
        assert merged.source == "src"

    def test_unknown_additional_keys_are_dropped(self, fixed_clock):
        base = DocumentMetadata(doc_id="d1")
        merged = merge_metadata(base, {"bogus_field": 42})
        assert not hasattr(merged, "bogus_field")

    def test_tags_and_custom_fields_copied_by_value(self, fixed_clock):
        base = DocumentMetadata(doc_id="d1", tags=["a"], custom_fields={"k": 1})
        merged = merge_metadata(base, {})
        merged.tags.append("b")
        merged.custom_fields["j"] = 2
        assert base.tags == ["a"]
        assert base.custom_fields == {"k": 1}
