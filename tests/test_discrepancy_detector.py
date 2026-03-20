"""Tests for DiscrepancyDetector."""

from __future__ import annotations

import pytest

from src.reconciliation.comparator import FieldComparator
from src.reconciliation.discrepancy_detector import DiscrepancyDetector
from src.reconciliation.matcher import MatchedPair
from tests.conftest import make_canonical_row


@pytest.fixture
def detector():
    schema = {
        "fields": [
            {"field_id": "id", "is_key": True},
            {"field_id": "name", "is_key": False},
            {"field_id": "amount", "is_key": False},
        ]
    }
    return DiscrepancyDetector(
        target_schema=schema,
        comparison_rules=[],
        comparator=FieldComparator(),
    )


class TestDetect:
    def test_no_discrepancies(self, detector):
        pair = MatchedPair(
            key="1",
            source_row=make_canonical_row({"id": "1", "name": "Alice", "amount": "100"}),
            target_row=make_canonical_row({"id": "1", "name": "Alice", "amount": "100"}),
        )
        result = detector.detect([pair])
        assert len(result) == 0

    def test_single_field_discrepancy(self, detector):
        pair = MatchedPair(
            key="1",
            source_row=make_canonical_row({"id": "1", "name": "Alice", "amount": "100"}),
            target_row=make_canonical_row({"id": "1", "name": "Bob", "amount": "100"}),
        )
        result = detector.detect([pair])
        assert len(result) == 1
        assert result[0].field_discrepancies[0].field_id == "name"

    def test_multiple_field_discrepancies(self, detector):
        pair = MatchedPair(
            key="1",
            source_row=make_canonical_row({"id": "1", "name": "Alice", "amount": "100"}),
            target_row=make_canonical_row({"id": "1", "name": "Bob", "amount": "200"}),
        )
        result = detector.detect([pair])
        assert len(result) == 1
        assert len(result[0].field_discrepancies) == 2

    def test_stores_full_records(self, detector):
        pair = MatchedPair(
            key="1",
            source_row=make_canonical_row({"id": "1", "name": "A", "amount": "100"}),
            target_row=make_canonical_row({"id": "1", "name": "B", "amount": "100"}),
        )
        result = detector.detect([pair])
        assert result[0].source_record == {"id": "1", "name": "A", "amount": "100"}


class TestIgnoreField:
    def test_ignored_field_not_compared(self):
        schema = {"fields": [
            {"field_id": "id", "is_key": True},
            {"field_id": "name", "is_key": False},
        ]}
        rules = [{"target_field_id": "name", "ignore_field": True, "is_active": True}]
        det = DiscrepancyDetector(target_schema=schema, comparison_rules=rules, comparator=FieldComparator())
        pair = MatchedPair(
            key="1",
            source_row=make_canonical_row({"id": "1", "name": "Alice"}),
            target_row=make_canonical_row({"id": "1", "name": "Bob"}),
        )
        result = det.detect([pair])
        assert len(result) == 0


class TestComparisonRules:
    def test_numeric_tolerance_rule(self):
        schema = {"fields": [
            {"field_id": "id", "is_key": True},
            {"field_id": "amount", "is_key": False},
        ]}
        rules = [{
            "target_field_id": "amount",
            "comparator_type": "NUMERIC_TOLERANCE",
            "comparator_params": {"tolerance": 0.1, "tolerance_type": "ABSOLUTE"},
            "is_active": True,
        }]
        det = DiscrepancyDetector(target_schema=schema, comparison_rules=rules, comparator=FieldComparator())
        pair = MatchedPair(
            key="1",
            source_row=make_canonical_row({"id": "1", "amount": "100.00"}),
            target_row=make_canonical_row({"id": "1", "amount": "100.05"}),
        )
        result = det.detect([pair])
        assert len(result) == 0
