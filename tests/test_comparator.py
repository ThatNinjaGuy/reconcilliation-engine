"""Tests for the FieldComparator."""

from __future__ import annotations

import pytest

from src.reconciliation.comparator import FieldComparator


@pytest.fixture
def comparator():
    return FieldComparator()


class TestExactComparator:
    def test_equal_strings(self, comparator):
        ok, _ = comparator.compare("hello", "hello", "EXACT")
        assert ok is True

    def test_different_strings(self, comparator):
        ok, diff = comparator.compare("hello", "world", "EXACT")
        assert ok is False
        assert diff is not None

    def test_both_none(self, comparator):
        ok, _ = comparator.compare(None, None, "EXACT")
        assert ok is True

    def test_one_none(self, comparator):
        ok, _ = comparator.compare("a", None, "EXACT")
        assert ok is False

    def test_type_coercion(self, comparator):
        ok, _ = comparator.compare("100", 100, "EXACT")
        assert ok is True

    def test_zero_is_equal(self, comparator):
        ok, _ = comparator.compare(0, 0, "EXACT")
        assert ok is True


class TestNumericTolerance:
    def test_within_absolute_tolerance(self, comparator):
        ok, _ = comparator.compare(100.0, 100.005, "NUMERIC_TOLERANCE", {"tolerance": 0.01, "tolerance_type": "ABSOLUTE"})
        assert ok is True

    def test_outside_absolute_tolerance(self, comparator):
        ok, _ = comparator.compare(100.0, 100.05, "NUMERIC_TOLERANCE", {"tolerance": 0.01, "tolerance_type": "ABSOLUTE"})
        assert ok is False

    def test_within_percentage_tolerance(self, comparator):
        ok, _ = comparator.compare(100, 101, "NUMERIC_TOLERANCE", {"tolerance": 2, "tolerance_type": "PERCENTAGE"})
        assert ok is True


class TestCaseInsensitive:
    def test_case_match(self, comparator):
        ok, _ = comparator.compare("Hello", "hello", "CASE_INSENSITIVE")
        assert ok is True

    def test_case_mismatch(self, comparator):
        ok, _ = comparator.compare("Hello", "World", "CASE_INSENSITIVE")
        assert ok is False


class TestNullEqualsEmpty:
    def test_null_equals_empty(self, comparator):
        ok, _ = comparator.compare(None, "", "NULL_EQUALS_EMPTY")
        assert ok is True

    def test_empty_equals_null(self, comparator):
        ok, _ = comparator.compare("", None, "NULL_EQUALS_EMPTY")
        assert ok is True

    def test_both_null(self, comparator):
        ok, _ = comparator.compare(None, None, "NULL_EQUALS_EMPTY")
        assert ok is True

    def test_different_values(self, comparator):
        ok, _ = comparator.compare("a", "b", "NULL_EQUALS_EMPTY")
        assert ok is False


class TestUnknownComparator:
    def test_raises_on_unknown(self, comparator):
        with pytest.raises(ValueError, match="Unknown comparator"):
            comparator.compare("a", "b", "NONEXISTENT")
