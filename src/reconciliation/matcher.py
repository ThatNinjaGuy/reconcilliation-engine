"""Record matcher implementation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List
import logging

from ..connectors.base import CanonicalRow

logger = logging.getLogger(__name__)


@dataclass
class MatchedPair:
    key: str
    source_row: CanonicalRow
    target_row: CanonicalRow
    metadata: Dict[str, Any] | None = None


@dataclass
class MatchResult:
    matched_pairs: List[MatchedPair]
    unmatched_source: List[CanonicalRow]
    unmatched_target: List[CanonicalRow]
    match_stats: Dict[str, Any]


class RecordMatcher:
    """Matches source and target records using matching keys."""

    def __init__(self, matching_config: Dict[str, Any]):
        self.matching_config = matching_config
        self.matching_keys = matching_config["matching_keys"]
        self.matching_strategy = matching_config.get("matching_strategy", "EXACT")

    def match(self, source_rows: List[CanonicalRow], target_rows: List[CanonicalRow]) -> MatchResult:
        start_time = datetime.utcnow()

        if self.matching_strategy == "EXACT":
            result = self._exact_match(source_rows, target_rows)
        elif self.matching_strategy == "FUZZY":
            raise NotImplementedError("Fuzzy matching not yet implemented")
        else:
            raise ValueError(f"Unknown matching strategy: {self.matching_strategy}")

        result.match_stats = {
            "total_source": len(source_rows),
            "total_target": len(target_rows),
            "matched": len(result.matched_pairs),
            "unmatched_source": len(result.unmatched_source),
            "unmatched_target": len(result.unmatched_target),
            "match_rate": len(result.matched_pairs) / max(len(source_rows), 1) * 100,
            "duration_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
        }

        logger.info(
            "Matched %s of %s source records (%.2f%%)",
            result.match_stats["matched"],
            result.match_stats["total_source"],
            result.match_stats["match_rate"],
        )
        return result

    def _exact_match(self, source_rows: List[CanonicalRow], target_rows: List[CanonicalRow]) -> MatchResult:
        source_index = self._build_index(source_rows, "source")
        target_index = self._build_index(target_rows, "target")

        source_keys = set(source_index.keys())
        target_keys = set(target_index.keys())

        matched_keys = source_keys & target_keys
        unmatched_source_keys = source_keys - target_keys
        unmatched_target_keys = target_keys - source_keys

        matched_pairs: List[MatchedPair] = []
        for key in matched_keys:
            source_list = source_index[key]
            target_list = target_index[key]
            matched_pairs.append(
                MatchedPair(
                    key=key,
                    source_row=source_list[0],
                    target_row=target_list[0],
                    metadata={"source_count": len(source_list), "target_count": len(target_list)},
                )
            )
            if len(source_list) > 1 or len(target_list) > 1:
                logger.warning("Duplicate key %s: %s source, %s target", key, len(source_list), len(target_list))

        unmatched_source: List[CanonicalRow] = []
        for key in unmatched_source_keys:
            unmatched_source.extend(source_index[key])
        unmatched_target: List[CanonicalRow] = []
        for key in unmatched_target_keys:
            unmatched_target.extend(target_index[key])

        return MatchResult(
            matched_pairs=matched_pairs,
            unmatched_source=unmatched_source,
            unmatched_target=unmatched_target,
            match_stats={},
        )

    def _build_index(self, rows: List[CanonicalRow], side: str) -> Dict[str, List[CanonicalRow]]:
        index: Dict[str, List[CanonicalRow]] = {}
        for row in rows:
            key = self.extract_matching_key(row, side)
            index.setdefault(key, []).append(row)
        return index

    def extract_matching_key(self, row: CanonicalRow, side: str) -> str:
        key_parts = []
        norm = self.matching_config.get("key_normalization", {})
        trim_whitespace = norm.get("trim_whitespace", False)
        for key_config in self.matching_keys:
            field_name = key_config[f"{side}_field"]
            is_case_sensitive = key_config.get("is_case_sensitive", True)
            value = row.get_field(field_name)
            if value is None:
                value = ""
            else:
                value = str(value)
                if trim_whitespace:
                    value = value.strip()
                if not is_case_sensitive:
                    value = value.lower()
            key_parts.append(value)
        return "|".join(key_parts)
