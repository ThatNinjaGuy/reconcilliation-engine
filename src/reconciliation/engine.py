"""Reconciliation orchestration logic."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List
import logging

from ..connectors.base import CanonicalRow
from .matcher import MatchResult, RecordMatcher
from .comparator import FieldComparator
from .discrepancy_detector import DiscrepancyDetector, RecordDiscrepancy

logger = logging.getLogger(__name__)


@dataclass
class ReconciliationResult:
    rule_set_id: str
    match_result: MatchResult
    record_discrepancies: List[RecordDiscrepancy]
    summary_stats: Dict[str, Any]
    run_metadata: Dict[str, Any]


class ReconciliationEngine:
    """Main reconciliation engine."""

    def __init__(
        self,
        rule_set: Dict[str, Any],
        target_schema: Dict[str, Any],
        comparison_rules: List[Dict[str, Any]],
    ):
        self.rule_set = rule_set
        self.target_schema = target_schema
        self.comparison_rules = comparison_rules
        self.matcher = RecordMatcher(rule_set)
        self.comparator = FieldComparator()
        self.detector = DiscrepancyDetector(
            target_schema=target_schema,
            comparison_rules=comparison_rules,
            comparator=self.comparator,
        )

    def reconcile(
        self,
        source_rows: List[CanonicalRow],
        target_rows: List[CanonicalRow],
    ) -> ReconciliationResult:
        start_time = datetime.utcnow()
        logger.info("Starting reconciliation: %s source, %s target rows", len(source_rows), len(target_rows))

        match_result = self.matcher.match(source_rows, target_rows)
        record_discrepancies = self.detector.detect(match_result.matched_pairs)
        summary_stats = self._calculate_summary_stats(match_result, record_discrepancies)

        run_metadata = {
            "rule_set_id": self.rule_set["rule_set_id"],
            "started_at": start_time.isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
            "duration_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
        }

        return ReconciliationResult(
            rule_set_id=self.rule_set["rule_set_id"],
            match_result=match_result,
            record_discrepancies=record_discrepancies,
            summary_stats=summary_stats,
            run_metadata=run_metadata,
        )

    def _calculate_summary_stats(
        self,
        match_result: MatchResult,
        record_discrepancies: List[RecordDiscrepancy],
    ) -> Dict[str, Any]:
        total_matched = len(match_result.matched_pairs)
        matched_with_discrepancy = len(record_discrepancies)
        matched_with_no_discrepancy = total_matched - matched_with_discrepancy

        field_discrepancy_counts: Dict[str, int] = {}
        total_field_discrepancies = 0
        for record_disc in record_discrepancies:
            for field_disc in record_disc.field_discrepancies:
                field_discrepancy_counts[field_disc.field_id] = (
                    field_discrepancy_counts.get(field_disc.field_id, 0) + 1
                )
                total_field_discrepancies += 1

        return {
            "total_source_records": match_result.match_stats["total_source"],
            "total_target_records": match_result.match_stats["total_target"],
            "matched_records": total_matched,
            "matched_with_no_discrepancy": matched_with_no_discrepancy,
            "matched_with_discrepancy": matched_with_discrepancy,
            "unmatched_source_records": len(match_result.unmatched_source),
            "unmatched_target_records": len(match_result.unmatched_target),
            "total_field_discrepancies": total_field_discrepancies,
            "field_discrepancy_counts": field_discrepancy_counts,
            "match_rate_percent": match_result.match_stats["match_rate"],
            "accuracy_rate_percent": (matched_with_no_discrepancy / max(total_matched, 1)) * 100,
        }
