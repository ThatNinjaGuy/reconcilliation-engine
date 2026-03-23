"""Discrepancy detection for matched records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
import logging

from .matcher import MatchedPair
from .comparator import FieldComparator

logger = logging.getLogger(__name__)


@dataclass
class FieldDiscrepancy:
    key: str
    field_id: str
    source_value: Any
    target_value: Any
    difference: str
    comparator_type: str
    severity: str = "ERROR"


@dataclass
class RecordDiscrepancy:
    key: str
    field_discrepancies: List[FieldDiscrepancy]
    source_metadata: Dict[str, Any]
    target_metadata: Dict[str, Any]
    source_record: Dict[str, Any]
    target_record: Dict[str, Any]


class DiscrepancyDetector:
    """Detect field-level discrepancies in matched pairs."""

    def __init__(
        self,
        target_schema: Dict[str, Any],
        comparison_rules: List[Dict[str, Any]],
        comparator: FieldComparator,
    ):
        self.target_schema = target_schema
        self.comparison_rules = comparison_rules
        self.comparator = comparator
        self.rules_by_field = {
            rule["target_field_id"]: rule
            for rule in comparison_rules
            if rule.get("is_active", True)
        }

    def detect(self, matched_pairs: List[MatchedPair]) -> List[RecordDiscrepancy]:
        record_discrepancies: List[RecordDiscrepancy] = []
        for pair in matched_pairs:
            field_discrepancies = self._compare_record_pair(pair)
            if field_discrepancies:
                record_discrepancies.append(
                    RecordDiscrepancy(
                        key=pair.key,
                        field_discrepancies=field_discrepancies,
                        source_metadata=pair.source_row.metadata,
                        target_metadata=pair.target_row.metadata,
                        source_record=dict(pair.source_row.fields),
                        target_record=dict(pair.target_row.fields),
                    )
                )
        logger.info("Found discrepancies in %s matched records", len(record_discrepancies))
        return record_discrepancies

    def _compare_record_pair(self, pair: MatchedPair) -> List[FieldDiscrepancy]:
        field_discrepancies: List[FieldDiscrepancy] = []
        target_fields = self.target_schema["fields"]
        for field_def in target_fields:
            field_id = field_def["field_id"]
            rule = self.rules_by_field.get(field_id)
            if rule and rule.get("ignore_field", False):
                continue
            comparator_type = rule.get("comparator_type", "EXACT") if rule else "EXACT"
            comparator_params = rule.get("comparator_params", {}) if rule else {}

            source_value = pair.source_row.get_field(field_id)
            target_value = pair.target_row.get_field(field_id)

            try:
                values_match, difference = self.comparator.compare(
                    source_value, target_value, comparator_type, comparator_params
                )
                if not values_match:
                    field_discrepancies.append(
                        FieldDiscrepancy(
                            key=pair.key,
                            field_id=field_id,
                            source_value=source_value,
                            target_value=target_value,
                            difference=difference or "Values differ",
                            comparator_type=comparator_type,
                            severity="ERROR",
                        )
                    )
            except Exception as exc:
                logger.error("Comparison failed for field %s: %s", field_id, exc)
                field_discrepancies.append(
                    FieldDiscrepancy(
                        key=pair.key,
                        field_id=field_id,
                        source_value=source_value,
                        target_value=target_value,
                        difference=f"Comparison error: {exc}",
                        comparator_type=comparator_type,
                        severity="WARNING",
                    )
                )
        return field_discrepancies
