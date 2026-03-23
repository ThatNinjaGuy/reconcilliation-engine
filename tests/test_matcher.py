"""Tests for the RecordMatcher."""

from __future__ import annotations

import pytest

from src.reconciliation.matcher import RecordMatcher, MatchedPair
from tests.conftest import make_canonical_row


class TestExactMatch:
    def _matcher(self, **overrides):
        config = {
            "matching_keys": [{"source_field": "id", "target_field": "id", "is_case_sensitive": True}],
            "matching_strategy": "EXACT",
        }
        config.update(overrides)
        return RecordMatcher(config)

    def test_all_matched(self):
        src = [make_canonical_row({"id": "1", "v": "a"}), make_canonical_row({"id": "2", "v": "b"})]
        tgt = [make_canonical_row({"id": "1", "v": "a"}), make_canonical_row({"id": "2", "v": "b"})]
        result = self._matcher().match(src, tgt)
        assert len(result.matched_pairs) == 2
        assert len(result.unmatched_source) == 0
        assert len(result.unmatched_target) == 0

    def test_unmatched_both_sides(self):
        src = [make_canonical_row({"id": "1"}), make_canonical_row({"id": "3"})]
        tgt = [make_canonical_row({"id": "1"}), make_canonical_row({"id": "2"})]
        result = self._matcher().match(src, tgt)
        assert len(result.matched_pairs) == 1
        assert len(result.unmatched_source) == 1
        assert result.unmatched_source[0].get_field("id") == "3"
        assert len(result.unmatched_target) == 1
        assert result.unmatched_target[0].get_field("id") == "2"

    def test_empty_source(self):
        tgt = [make_canonical_row({"id": "1"})]
        result = self._matcher().match([], tgt)
        assert len(result.matched_pairs) == 0
        assert len(result.unmatched_target) == 1

    def test_empty_both(self):
        result = self._matcher().match([], [])
        assert len(result.matched_pairs) == 0

    def test_duplicate_keys(self):
        src = [make_canonical_row({"id": "1", "v": "first"}), make_canonical_row({"id": "1", "v": "second"})]
        tgt = [make_canonical_row({"id": "1", "v": "target"})]
        result = self._matcher().match(src, tgt)
        assert len(result.matched_pairs) == 1
        assert result.matched_pairs[0].metadata["source_count"] == 2

    def test_case_sensitive_keys(self):
        src = [make_canonical_row({"id": "ABC"})]
        tgt = [make_canonical_row({"id": "abc"})]
        result = self._matcher().match(src, tgt)
        assert len(result.matched_pairs) == 0

    def test_case_insensitive_keys(self):
        src = [make_canonical_row({"id": "ABC"})]
        tgt = [make_canonical_row({"id": "abc"})]
        m = self._matcher(matching_keys=[{"source_field": "id", "target_field": "id", "is_case_sensitive": False}])
        result = m.match(src, tgt)
        assert len(result.matched_pairs) == 1

    def test_composite_key(self):
        src = [make_canonical_row({"a": "1", "b": "x"})]
        tgt = [make_canonical_row({"a": "1", "b": "x"})]
        m = self._matcher(matching_keys=[
            {"source_field": "a", "target_field": "a", "is_case_sensitive": True},
            {"source_field": "b", "target_field": "b", "is_case_sensitive": True},
        ])
        result = m.match(src, tgt)
        assert len(result.matched_pairs) == 1

    def test_trim_whitespace(self):
        src = [make_canonical_row({"id": "  1  "})]
        tgt = [make_canonical_row({"id": "1"})]
        m = self._matcher(key_normalization={"trim_whitespace": True})
        result = m.match(src, tgt)
        assert len(result.matched_pairs) == 1


class TestExtractMatchingKeyPublic:
    def test_public_method_exists(self):
        m = RecordMatcher({"matching_keys": [{"source_field": "id", "target_field": "id"}]})
        row = make_canonical_row({"id": "42"})
        assert m.extract_matching_key(row, "source") == "42"

    def test_null_key_value(self):
        m = RecordMatcher({"matching_keys": [{"source_field": "id", "target_field": "id"}]})
        row = make_canonical_row({"id": None})
        assert m.extract_matching_key(row, "source") == ""
